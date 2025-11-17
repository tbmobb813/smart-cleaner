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
def cli():
    """SmartCleaner CLI: inspect and restore clean operations."""
    pass


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


def main():
    cli()
