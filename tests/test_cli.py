import click
from click.testing import CliRunner
from smartcleaner.cli.commands import cli
from smartcleaner.db.operations import DatabaseManager
from smartcleaner.managers.undo_manager import UndoManager
from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel


def test_cli_list_and_show(tmp_path):
    # Setup DB and a logged operation
    db_path = tmp_path / 'cli.db'
    db = DatabaseManager(db_path=db_path)
    undo = UndoManager(db=db, backup_dir=tmp_path / 'backups')

    f = tmp_path / 'a.txt'
    f.write_text('x')
    item = CleanableItem(path=str(f), size=1, description='t', safety=SafetyLevel.SAFE)
    op_id = undo.log_operation('plug', [item])

    runner = CliRunner()
    result = runner.invoke(cli, ['list', '--db', str(db_path)])
    assert result.exit_code == 0
    assert str(op_id) in result.output

    result = runner.invoke(cli, ['show', str(op_id), '--db', str(db_path)])
    assert result.exit_code == 0
    assert 'Undo items' in result.output


def test_cli_restore_dry_run_and_confirm(tmp_path, monkeypatch):
    db_path = tmp_path / 'cli2.db'
    db = DatabaseManager(db_path=db_path)
    undo = UndoManager(db=db, backup_dir=tmp_path / 'backups')

    f = tmp_path / 'b.txt'
    f.write_text('y')
    item = CleanableItem(path=str(f), size=1, description='t', safety=SafetyLevel.SAFE)
    op_id = undo.log_operation('plug', [item])

    runner = CliRunner()
    # dry-run should not change files
    result = runner.invoke(cli, ['restore', str(op_id), '--db', str(db_path), '--dry-run'])
    assert result.exit_code == 0
    assert 'Dry-run' in result.output

    # confirm path: simulate user saying yes
    monkeypatch.setattr('click.confirm', lambda *a, **k: True)
    result = runner.invoke(cli, ['restore', str(op_id), '--db', str(db_path)])
    assert result.exit_code == 0
    assert 'Restored' in result.output
