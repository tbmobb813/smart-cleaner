from __future__ import annotations

import click
from typing import Optional, Any
from pathlib import Path
from smartcleaner.db.operations import DatabaseManager
from smartcleaner.managers.undo_manager import UndoManager
import importlib
import inspect


def _human_size(num: float) -> str:
    # simple human-readable size
    val = float(num)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(val) < 1024.0:
            return f"{val:.1f}{unit}"
        val /= 1024.0
    return f"{val:.1f}PB"


def _get_db(db_path: Optional[str] = None) -> DatabaseManager:
    if db_path is None:
        return DatabaseManager(db_path=None)
    return DatabaseManager(db_path=Path(db_path))


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--quiet', '-q', is_flag=True, help='Suppress most output')
@click.pass_context
def cli(ctx, verbose: bool, quiet: bool):
    """SmartCleaner CLI: inspect and restore clean operations."""
    from smartcleaner.utils.logging_config import setup_cli_logging

    # Store flags in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet

    # Setup logging
    setup_cli_logging(verbose=verbose, quiet=quiet)


@cli.group('schema')
def schema_group():
    """Schema operations"""
    pass


@schema_group.command('show')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
def schema_show(db: Optional[str]):
    """Show DB schema version."""
    dbm = _get_db(db)
    click.echo(f"schema_version: {dbm.get_schema_version()}")


@schema_group.command('migrate')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
@click.option('--apply', is_flag=True, help='Apply pending migrations')
def schema_migrate(db: Optional[str], apply: bool):
    """Show pending migrations and optionally apply them."""
    dbm = _get_db(db)
    pending = dbm.get_pending_migrations()
    if not pending:
        click.echo('No pending migrations.')
        return
    click.echo(f'Pending migrations: {pending}')
    if apply:
        applied = dbm.apply_migrations()
        click.echo(f'Applied migrations: {applied}')


@cli.command('list')
@click.option('--limit', '-n', default=10, help='How many recent operations to list')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
def list_ops(limit: int, db: Optional[str]):
    dbm = _get_db(db)
    ops = dbm.get_recent_operations(limit=limit)
    if not ops:
        click.echo('No operations found')
        return
    for o in ops:
        size_h = _human_size(o.get('size_freed', 0))
        click.echo(f"{o['id']}: {click.style(o['plugin_name'], fg='cyan')} items={o['items_count']} size={click.style(size_h, fg='yellow')} ts={o['timestamp']}")


@cli.command('show')
@click.argument('operation_id', type=int)
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
def show_op(operation_id: int, db: Optional[str]):
    dbm = _get_db(db)
    ops = dbm.get_recent_operations(limit=100)
    op = next((o for o in ops if o['id'] == operation_id), None)
    if not op:
        click.echo(f'Operation {operation_id} not found')
        return
    size_h = _human_size(op.get('size_freed', 0))
    click.echo(f"Operation {op['id']}: {click.style(op['plugin_name'], fg='cyan')} ({op['timestamp']})\n  items={op['items_count']} size={click.style(size_h, fg='yellow')} success={bool(op['success'])}")
    items = dbm.get_undo_items(operation_id)
    if not items:
        click.echo('  no undo items recorded')
        return
    click.echo('  Undo items:')
    for it in items:
        click.echo(f"    {it['id']}: path={it['item_path']} backup={it.get('backup_path')} restored={it.get('restored',0)}")


@cli.command('restore')
@click.argument('operation_id', type=int)
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
@click.option('--yes', is_flag=True, help='Run without confirmation')
@click.option('--dry-run', is_flag=True, help='Show what would be restored without changing files')
@click.option('--conflict-policy', type=click.Choice(['rename','overwrite','skip']), default='rename', help='What to do when destination exists')
def restore_op(operation_id: int, db: Optional[str], yes: bool, dry_run: bool, conflict_policy: str):
    dbm = _get_db(db)
    undo = UndoManager(db=dbm)
    items = dbm.get_undo_items(operation_id)
    if not items:
        click.echo(f'No undo items found for operation {operation_id}')
        return

    click.echo(f'Operation {operation_id} has {len(items)} undo items:')
    for it in items:
        click.echo(f"  {it['id']}: {it['item_path']} (backup={it.get('backup_path')})")

    if dry_run:
        click.echo('Dry-run: no changes will be made.')
        return

    if not yes:
        confirmed = click.confirm(f'Proceed to restore operation {operation_id}?')
        if not confirmed:
            click.echo('Aborted.')
            return

    results = undo.restore_operation(operation_id, conflict_policy=conflict_policy)
    success = sum(1 for v in results.values() if v)
    click.echo(f'Restored {success}/{len(results)} items')


@cli.command('gc')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
@click.option('--keep-last', type=int, default=None, help='Keep the N most recent backups')
@click.option('--older-than-days', type=int, default=None, help='Remove backups older than days')
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
def gc_cmd(db: Optional[str], keep_last: Optional[int], older_than_days: Optional[int], yes: bool):
    dbm = _get_db(db)
    undo = UndoManager(db=dbm)
    if not yes:
        confirmed = click.confirm(f'Prune backups with keep_last={keep_last} older_than_days={older_than_days}?')
        if not confirmed:
            click.echo('Aborted.')
            return
    res = undo.prune_backups(keep_last=keep_last, older_than_days=older_than_days)
    click.echo(f"Pruned: removed={res['removed']} remaining={res['remaining']}")


@cli.command('scan')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
@click.option('--safety', type=click.Choice(['SAFE', 'CAUTION', 'ADVANCED', 'DANGEROUS']), default='CAUTION', help='Maximum safety level to include')
@click.option('--plugin', default=None, help='Scan only this plugin (optional)')
def scan_cmd(db: Optional[str], safety: str, plugin: Optional[str]):
    """Scan for cleanable items."""
    from smartcleaner.managers.cleaner_manager import CleanerManager, SafetyLevel

    dbm = _get_db(db)
    manager = CleanerManager(db_manager=dbm)

    # Convert safety string to enum
    safety_level = SafetyLevel[safety]

    if plugin:
        # Scan specific plugin
        try:
            items = manager.scan_plugin(plugin, safety_filter=safety_level)
            if not items:
                click.echo(f"No items found for plugin '{plugin}'")
                return

            click.echo(f"\n{click.style(plugin, fg='cyan', bold=True)}")
            click.echo(f"Found {len(items)} items:")
            total_size = 0
            for item in items:
                size_h = _human_size(item.size)
                safety_color = 'green' if item.safety == SafetyLevel.SAFE else 'yellow'
                click.echo(f"  [{click.style(item.safety.name, fg=safety_color)}] {item.description} ({size_h})")
                total_size += item.size
            click.echo(f"Total: {click.style(_human_size(total_size), fg='yellow', bold=True)}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            return
    else:
        # Scan all plugins
        results = manager.scan_all(safety_filter=safety_level)

        if not results:
            click.echo('No cleanable items found.')
            return

        grand_total = 0
        for plugin_name, items in results.items():
            click.echo(f"\n{click.style(plugin_name, fg='cyan', bold=True)}")
            click.echo(f"Found {len(items)} items:")
            plugin_total = 0
            for item in items[:5]:  # Show first 5 items
                size_h = _human_size(item.size)
                safety_color = 'green' if item.safety == SafetyLevel.SAFE else 'yellow'
                click.echo(f"  [{click.style(item.safety.name, fg=safety_color)}] {item.description} ({size_h})")
                plugin_total += item.size

            if len(items) > 5:
                remaining = len(items) - 5
                remaining_size = sum(i.size for i in items[5:])
                click.echo(f"  ... and {remaining} more items ({_human_size(remaining_size)})")
                plugin_total += remaining_size

            click.echo(f"Subtotal: {click.style(_human_size(plugin_total), fg='yellow')}")
            grand_total += plugin_total

        click.echo(f"\n{click.style('Grand Total:', bold=True)} {click.style(_human_size(grand_total), fg='yellow', bold=True)}")


@cli.command('clean')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
@click.option('--safety', type=click.Choice(['SAFE', 'CAUTION', 'ADVANCED', 'DANGEROUS']), default='CAUTION', help='Maximum safety level to clean')
@click.option('--plugin', default=None, help='Clean only this plugin (optional)')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without cleaning')
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
def clean_cmd(db: Optional[str], safety: str, plugin: Optional[str], dry_run: bool, yes: bool):
    """Clean items found by scan."""
    from smartcleaner.managers.cleaner_manager import CleanerManager, SafetyLevel
    import os

    dbm = _get_db(db)
    manager = CleanerManager(db_manager=dbm)

    # Convert safety string to enum
    safety_level = SafetyLevel[safety]

    # Scan first
    if plugin:
        try:
            items = manager.scan_plugin(plugin, safety_filter=safety_level)
            if not items:
                click.echo(f"No items found for plugin '{plugin}'")
                return
            items_by_plugin = {plugin: items}
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            return
    else:
        items_by_plugin = manager.scan_all(safety_filter=safety_level)

    if not items_by_plugin:
        click.echo('No cleanable items found.')
        return

    # Show what will be cleaned
    total_items = sum(len(items) for items in items_by_plugin.values())
    total_size = sum(sum(item.size for item in items) for items in items_by_plugin.values())

    click.echo(f"\nWill clean {total_items} items ({_human_size(total_size)}) from {len(items_by_plugin)} plugins:")
    for plugin_name, items in items_by_plugin.items():
        plugin_size = sum(item.size for item in items)
        click.echo(f"  {click.style(plugin_name, fg='cyan')}: {len(items)} items ({_human_size(plugin_size)})")

    if dry_run:
        click.echo(f"\n{click.style('DRY-RUN MODE', fg='yellow', bold=True)} - no changes will be made.")
        # Still perform dry-run to show results
        results = manager.clean_selected(items_by_plugin, dry_run=True)
        click.echo("\nDry-run results:")
        for plugin_name, result in results.items():
            status = click.style('✓', fg='green') if result['success'] else click.style('✗', fg='red')
            click.echo(f"  {status} {plugin_name}: would clean {result['cleaned_count']} items")
        return

    # Ask for confirmation unless --yes flag
    if not yes:
        # Check if we need sudo for any operations
        requires_sudo = any('apt' in p.lower() or 'journal' in p.lower() or 'kernel' in p.lower()
                          for p in items_by_plugin.keys())

        if requires_sudo:
            click.echo(f"\n{click.style('WARNING:', fg='red', bold=True)} This operation may require sudo privileges.")
            sudo_allowed = os.environ.get('SMARTCLEANER_ALLOW_SUDO')
            if not sudo_allowed:
                click.echo("Set SMARTCLEANER_ALLOW_SUDO=1 to allow automated sudo, or run commands manually.")

        confirmed = click.confirm(f'\nProceed with cleaning?')
        if not confirmed:
            click.echo('Aborted.')
            return

    # Perform cleaning
    click.echo('\nCleaning...')
    results = manager.clean_selected(items_by_plugin, dry_run=False)

    # Show results
    click.echo('\nResults:')
    total_cleaned = 0
    total_freed = 0
    for plugin_name, result in results.items():
        if result['success']:
            status = click.style('✓', fg='green')
            total_cleaned += result['cleaned_count']
            total_freed += result['total_size']
        else:
            status = click.style('✗', fg='red')

        size_h = _human_size(result['total_size'])
        click.echo(f"  {status} {plugin_name}: cleaned {result['cleaned_count']} items ({size_h})")

        if result.get('errors'):
            for error in result['errors']:
                click.echo(f"      {click.style('Error:', fg='red')} {error}")

    click.echo(f"\n{click.style('Total freed:', bold=True)} {click.style(_human_size(total_freed), fg='green', bold=True)}")


def main():
    cli()


@cli.group('clean')
def clean_group():
    """Cleaning commands (preview and remove)"""
    pass


@clean_group.command('apt-cache')
@click.option('--cache-dir', default=None, help='Path to APT cache dir (for testing)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted')
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
def clean_apt_cache(cache_dir: Optional[str], dry_run: bool, yes: bool, db: Optional[str]):
    """Clean APT package cache (uses apt-get clean when not dry-run)."""
    from smartcleaner.plugins.apt_cache import APTCacheCleaner
    from pathlib import Path
    from smartcleaner.managers.cleaner_manager import CleanerManager

    cache_path = Path(cache_dir) if cache_dir else Path('/var/cache/apt/archives')
    plugin = APTCacheCleaner(cache_dir=cache_path)

    # Use CleanerManager so cleaning goes through the centralized flow and is logged
    mgr = CleanerManager()
    # Ensure the manager uses our plugin instance (respecting cache_dir override)
    mgr.plugins[plugin.get_name()] = plugin

    items = plugin.scan()
    total = sum(i.size for i in items)
    click.echo(f"Found {len(items)} items totaling {_human_size(total)} in {cache_path}")
    for it in items:
        click.echo(f"  - {it.path} ({_human_size(it.size)}) {it.description}")

    if dry_run:
        click.echo('Dry-run: no changes will be made.')
        return

    if not yes:
        if not click.confirm(f'Proceed to clean APT cache at {cache_path}?'):
            click.echo('Aborted.')
            return

    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)
    res = results.get(plugin.get_name(), {})
    if res.get('success'):
        cleaned = res.get('cleaned_count', 0)
        freed = res.get('total_size', 0)
        op_id = res.get('operation_id')
        if op_id:
            click.echo(f"Cleaned {cleaned} items, freed {_human_size(freed)} (operation id: {op_id})")
        else:
            click.echo(f"Cleaned {cleaned} items, freed {_human_size(freed)}")
    else:
        click.echo(f"Errors: {res.get('errors')}")


@clean_group.command('browser-cache')
@click.option('--base-dir', default=None, help='Base cache dir to scan (for testing)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted')
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
def clean_browser_cache(base_dir: Optional[str], dry_run: bool, yes: bool):
    from smartcleaner.plugins.browser_cache import BrowserCacheCleaner
    from pathlib import Path
    from smartcleaner.managers.cleaner_manager import CleanerManager

    base = [Path(base_dir)] if base_dir else None
    plugin = BrowserCacheCleaner(base_dirs=base)
    mgr = CleanerManager()
    mgr.plugins[plugin.get_name()] = plugin

    items = plugin.scan()
    total = sum(i.size for i in items)
    click.echo(f"Found {len(items)} items totaling {_human_size(total)} in browser caches")
    if dry_run:
        click.echo('Dry-run: no changes will be made.')
        return

    if not yes:
        if not click.confirm('Proceed to clean browser caches?'):
            click.echo('Aborted.')
            return

    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)
    res = results.get(plugin.get_name(), {})
    if res.get('success'):
        click.echo(f"Cleaned {res.get('cleaned_count',0)} items, freed {_human_size(res.get('total_size',0))}")
    else:
        click.echo(f"Errors: {res.get('errors')}")


@clean_group.command('thumbnails')
@click.option('--cache-dir', default=None, help='Thumbnail cache dir (for testing)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted')
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
def clean_thumbnails(cache_dir: Optional[str], dry_run: bool, yes: bool):
    from smartcleaner.plugins.thumbnails import ThumbnailCacheCleaner
    from pathlib import Path
    from smartcleaner.managers.cleaner_manager import CleanerManager

    cache_path = Path(cache_dir) if cache_dir else None
    plugin = ThumbnailCacheCleaner(cache_dir=cache_path)
    mgr = CleanerManager()
    mgr.plugins[plugin.get_name()] = plugin

    items = plugin.scan()
    total = sum(i.size for i in items)
    click.echo(f"Found {len(items)} items totaling {_human_size(total)} in thumbnails cache")
    if dry_run:
        click.echo('Dry-run: no changes will be made.')
        return

    if not yes:
        if not click.confirm('Proceed to clean thumbnails cache?'):
            click.echo('Aborted.')
            return

    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)
    res = results.get(plugin.get_name(), {})
    if res.get('success'):
        click.echo(f"Cleaned {res.get('cleaned_count',0)} items, freed {_human_size(res.get('total_size',0))}")
    else:
        click.echo(f"Errors: {res.get('errors')}")


@clean_group.command('tmp')
@click.option('--base-dir', default=None, help='Base tmp dir to scan (for testing)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted')
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
def clean_tmp(base_dir: Optional[str], dry_run: bool, yes: bool):
    from smartcleaner.plugins.tmp_cleaner import TmpCleaner
    from pathlib import Path
    from smartcleaner.managers.cleaner_manager import CleanerManager

    base = Path(base_dir) if base_dir else None
    plugin = TmpCleaner(base_dir=base)
    mgr = CleanerManager()
    mgr.plugins[plugin.get_name()] = plugin

    items = plugin.scan()
    total = sum(i.size for i in items)
    click.echo(f"Found {len(items)} items totaling {_human_size(total)} in {base or '/tmp'}")
    if dry_run:
        click.echo('Dry-run: no changes will be made.')
        return

    if not yes:
        if not click.confirm(f'Proceed to clean temporary files in {base or "/tmp"}?'):
            click.echo('Aborted.')
            return

    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)
    res = results.get(plugin.get_name(), {})
    if res.get('success'):
        click.echo(f"Cleaned {res.get('cleaned_count',0)} items, freed {_human_size(res.get('total_size',0))}")
    else:
        click.echo(f"Errors: {res.get('errors')}")


@clean_group.command('kernels')
@click.option('--keep-kernels', type=int, default=None, help='How many recent kernels to keep (overrides default)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted')
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
@click.option('--db', default=None, help='Path to sqlite DB (optional)')
def clean_kernels(keep_kernels: Optional[int], dry_run: bool, yes: bool, db: Optional[str]):
    """Clean old kernels using apt (purge + autoremove)."""
    from smartcleaner.plugins.kernels import KernelCleaner
    from smartcleaner.config import get_keep_kernels
    from smartcleaner.managers.cleaner_manager import CleanerManager

    # If the CLI flag wasn't provided, consult persistent config/defaults
    if keep_kernels is None:
        keep_kernels = get_keep_kernels()

    # Instantiate with requested keep count when provided
    plugin = KernelCleaner(keep=keep_kernels)
    mgr = CleanerManager()
    # ensure manager uses our plugin instance
    mgr.plugins[plugin.get_name()] = plugin

    items = plugin.scan()
    total = sum(i.size for i in items)
    click.echo(f"Found {len(items)} items totaling {_human_size(total)} to consider for removal")
    for it in items:
        click.echo(f"  - {it.path} ({_human_size(it.size)}) {it.description}")

    if dry_run:
        click.echo('Dry-run: no changes will be made.')
        return

    if not yes:
        if not click.confirm('Proceed to purge selected old kernels?'):
            click.echo('Aborted.')
            return

    results = mgr.clean_selected({plugin.get_name(): items}, dry_run=False)
    res = results.get(plugin.get_name(), {})
    if res.get('success'):
        cleaned = res.get('cleaned_count', 0)
        freed = res.get('total_size', 0)
        op_id = res.get('operation_id')
        if op_id:
            click.echo(f"Cleaned {cleaned} items, freed {_human_size(freed)} (operation id: {op_id})")
        else:
            click.echo(f"Cleaned {cleaned} items, freed {_human_size(freed)}")
    else:
        click.echo(f"Errors: {res.get('errors')}")


@cli.group('config')
def config_group():
    """Manage persistent configuration (XDG config)."""
    pass


@config_group.command('set')
@click.argument('key', type=str)
@click.argument('value', type=str)
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
def config_set(key: str, value: str, yes: bool):
    """Set a config key. Supported keys: keep_kernels, db_path"""
    from smartcleaner.config import set_config_value, get_allowed_keys, _config_file_path

    allowed = get_allowed_keys()
    if key not in allowed:
        click.echo(f'Unsupported config key: {key}')
        return

    if not yes:
        click.echo(f'About to set {key} in {_config_file_path()} to {value}')
        if not click.confirm('Proceed?'):
            click.echo('Aborted.')
            return

    ok = set_config_value(key, value)
    if ok:
        click.echo(f'Set {key} = {value}')
    else:
        click.echo('Failed to set config (validation or IO error)')


@config_group.group('plugin')
def config_plugin_group():
    """Manage per-plugin persistent configuration."""
    pass


@config_plugin_group.command('set')
@click.argument('factory_key', type=str)
@click.argument('key', type=str)
@click.argument('value', type=str)
@click.option('--yes', is_flag=True, help='Do not ask for confirmation')
def config_plugin_set(factory_key: str, key: str, value: str, yes: bool):
    """Set a config value for a plugin factory (factory can be module:Class or module)."""
    from smartcleaner.config import set_plugin_config

    # derive module name
    module_name = factory_key.split(':', 1)[0]

    if not yes:
        click.echo(f'About to set plugin config {module_name}.{key} = {value}')
        if not click.confirm('Proceed?'):
            click.echo('Aborted.')
            return

    try:
        ok = set_plugin_config(module_name, key, value)
    except ValueError as e:
        click.echo(f'Validation error: {e}')
        return

    if ok:
        click.echo(f'Set {module_name}.{key} = {value}')
    else:
        click.echo('Failed to persist plugin config (IO error)')


@config_plugin_group.command('get')
@click.argument('factory_key', type=str)
@click.argument('key', type=str)
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def config_plugin_get(factory_key: str, key: str, as_json: bool):
    from smartcleaner.config import get_plugin_config
    import json

    module_name = factory_key.split(':', 1)[0]
    val = get_plugin_config(module_name, key)
    if as_json:
        click.echo(json.dumps({ 'module': module_name, 'key': key, 'value': val }, default=str))
    else:
        click.echo('' if val is None else str(val))


@config_group.command('get')
@click.argument('key', type=str)
@click.option('--defaults', is_flag=True, help='Show environment/config/code defaults for the key')
def config_get(key: str):
    from smartcleaner.config import load_config, get_effective_value

    if '--defaults' in click.get_current_context().args:
        # Print effective values (env, config, code default)
        eff = get_effective_value(key)
        if not eff:
            click.echo('')
            return
        click.echo(f"env: {eff.get('env')}")
        click.echo(f"config: {eff.get('config')}")
        click.echo(f"code_default: {eff.get('code_default')}")
        click.echo(f"effective: {eff.get('effective')}")
        return

    cfg = load_config() or {}
    if key in cfg:
        click.echo(cfg[key])
    else:
        click.echo('')


@cli.group('plugins')
def plugins_group():
    """Plugin discovery and metadata commands"""
    pass


@plugins_group.command('list')
@click.option('--brief', is_flag=True, help='Show brief output')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def plugins_list(brief: bool, as_json: bool):
    """List available plugin factories and basic metadata."""
    from smartcleaner.managers.cleaner_manager import CleanerManager
    import json

    mgr = CleanerManager()
    if as_json:
        meta = mgr.get_factories_metadata()
        # Serialize meta into JSON-friendly structures
        serializable = {}
        for k, v in meta.items():
            serializable[k] = {
                'module': v.get('module'),
                'class': v.get('class'),
                'name': (v.get('plugin_info') or {}).get('name') if v.get('plugin_info') else None,
                'description': (v.get('plugin_info') or {}).get('description') or v.get('description'),
                'plugin_info': v.get('plugin_info'),
            }

        click.echo(json.dumps(serializable, indent=2, sort_keys=True))
        return

    factories = mgr.list_available_factories()
    if not factories:
        click.echo('No plugins discovered')
        return

    for key in factories:
        # key format: module:ClassName
        name = ''
        desc = ''
        try:
            cls = mgr.plugin_factories.get(key)
            module_name, class_name = key.split(':', 1)
            if cls is None:
                mod = importlib.import_module(module_name)
                cls = getattr(mod, class_name, None)
            # check for module-level PLUGIN_INFO
            try:
                mod = importlib.import_module(module_name)
                info = getattr(mod, 'PLUGIN_INFO', None)
                if isinstance(info, dict):
                    name = info.get('name', '')
                    desc = info.get('description', '')
            except Exception:
                pass

            if not name and cls is not None:
                name = getattr(cls, '__name__', '')
            if not desc and cls is not None:
                desc = (cls.__doc__ or '').strip()

        except Exception:
            name = key
            desc = ''

        if brief:
            click.echo(f"{key}: {name}")
        else:
            click.echo(f"{key}\n  name: {name}\n  description: {desc}\n")


@plugins_group.command('show')
@click.argument('factory_key', type=str)
@click.option('--json', 'as_json', is_flag=True, help='Output metadata as JSON')
def plugins_show(factory_key: str, as_json: bool):
    """Show detailed metadata for a plugin factory key."""
    from smartcleaner.managers.cleaner_manager import CleanerManager

    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if factory_key not in factories:
        click.echo(f"Unknown factory: {factory_key}")
        return

    cls: Any = mgr.plugin_factories.get(factory_key)
    module_name, class_name = factory_key.split(':', 1)
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        mod = None

    info = None
    if mod is not None:
        info = getattr(mod, 'PLUGIN_INFO', None)

    if as_json:
        import json

        out = {
            'factory_key': factory_key,
            'plugin_info': info if isinstance(info, dict) else None,
            'config': info.get('config') if isinstance(info, dict) else None,
            'class': None,
            'doc': None,
            'constructor': None,
        }

        if cls is None and mod is not None:
            cls = getattr(mod, class_name, None)

        if cls is not None:
            out['class'] = f"{cls.__module__}.{cls.__name__}"
            out['doc'] = (cls.__doc__ or '').strip()

        # Prefer constructor/schema from PLUGIN_INFO when available (stable),
        # otherwise fall back to introspected signature
        if isinstance(info, dict) and info.get('constructor') is not None:
            out['constructor'] = info.get('constructor')
        else:
            try:
                if isinstance(cls, type):
                    sig = inspect.signature(cls)
                    params = [p for p in sig.parameters.values() if p.name != 'self']
                    out['constructor'] = [{
                        'name': p.name,
                        'kind': str(p.kind),
                        'default': None if p.default is inspect._empty else repr(p.default),
                        'annotation': None if p.annotation is inspect._empty else str(p.annotation),
                    } for p in params]
                else:
                    out['constructor'] = None
            except Exception:
                out['constructor'] = None

        click.echo(json.dumps(out, indent=2, sort_keys=True))
        return

    if cls is None and mod is not None:
        cls = getattr(mod, class_name, None)

    if cls is None:
        click.echo('No class found for factory')
        return

    click.echo(f"Class: {cls.__module__}.{cls.__name__}")
    doc = (cls.__doc__ or '').strip()
    if doc:
        click.echo(f"Doc: {doc}")

    # show constructor signature (excluding self)
    try:
        if isinstance(cls, type):
            sig = inspect.signature(cls)
            params = [p for p in sig.parameters.values() if p.name != 'self']
            click.echo('Constructor:')
            for p in params:
                click.echo(f"  {p}")
    except Exception:
        pass


@plugins_group.command('export-form')
@click.argument('factory_key', type=str)
@click.option('--json', 'as_json', is_flag=True, help='Output schema as JSON (default)')
def plugins_export_form(factory_key: str, as_json: bool):
    """Export a plugin's form/schema (derived from PLUGIN_INFO) as JSON."""
    from smartcleaner.managers.cleaner_manager import CleanerManager
    from smartcleaner.utils.json_schema import plugin_info_to_json_schema
    import json

    mgr = CleanerManager()
    factories = mgr.list_available_factories()
    if factory_key not in factories:
        click.echo(f"Unknown factory: {factory_key}")
        return

    module_name = factory_key.split(':', 1)[0]
    try:
        schema = plugin_info_to_json_schema(module_name)
    except Exception as e:
        click.echo(f"Error generating schema: {e}")
        return

    if as_json:
        click.echo(json.dumps(schema, indent=2, sort_keys=True))
    else:
        # default to JSON formatted output
        click.echo(json.dumps(schema, indent=2, sort_keys=True))

