from __future__ import annotations

import click
from typing import Optional
from pathlib import Path
from smartcleaner.db.operations import DatabaseManager
from smartcleaner.managers.undo_manager import UndoManager


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
