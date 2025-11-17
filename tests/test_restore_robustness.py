import shutil
import os
from pathlib import Path

from smartcleaner.db.operations import DatabaseManager
from smartcleaner.managers.undo_manager import UndoManager
from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel


def test_move_fallback_to_copy(tmp_path, monkeypatch):
    db = DatabaseManager(db_path=tmp_path / 'r1.db')
    f = tmp_path / 'x.txt'
    content = 'abc'
    f.write_text(content)

    undo = UndoManager(db=db, backup_dir=tmp_path / 'backups')
    item = CleanableItem(path=str(f), size=len(content), description='t', safety=SafetyLevel.SAFE)
    op_id = undo.log_operation('plug', [item])

    ui = undo.get_undo_items(op_id)[0]
    backup = Path(ui['backup_path'])
    # ensure backup exists
    assert backup.exists()

    # make shutil.move raise during restore to force fallback
    original_move = shutil.move

    def fake_move(src, dst):
        raise OSError('simulated cross-fs move failure')

    monkeypatch.setattr(shutil, 'move', fake_move)
    try:
        res = undo.restore_operation(op_id)
    finally:
        monkeypatch.setattr(shutil, 'move', original_move)

    assert ui['id'] in res
    assert res[ui['id']] is True
    # original should be restored
    assert Path(ui['item_path']).read_text() == content
    # backup should be removed
    assert not backup.exists()


def test_chown_permission_recorded(tmp_path, monkeypatch):
    db = DatabaseManager(db_path=tmp_path / 'r2.db')
    f = tmp_path / 'y.txt'
    content = 'zzz'
    f.write_text(content)

    undo = UndoManager(db=db, backup_dir=tmp_path / 'backups')
    item = CleanableItem(path=str(f), size=len(content), description='t', safety=SafetyLevel.SAFE)
    op_id = undo.log_operation('plug', [item])

    ui = undo.get_undo_items(op_id)[0]
    backup = Path(ui['backup_path'])
    assert backup.exists()

    # monkeypatch chown to raise PermissionError
    import os as _os

    real_chown = _os.chown

    def fake_chown(path, uid, gid):
        raise PermissionError('no permission')

    monkeypatch.setattr(_os, 'chown', fake_chown)
    try:
        res = undo.restore_operation(op_id)
    finally:
        monkeypatch.setattr(_os, 'chown', real_chown)

    assert ui['id'] in res
    assert res[ui['id']] is True
    # DB should record a restore_error mentioning chown
    updated = db.get_undo_items(op_id)[0]
    assert updated.get('restored') == 1
    assert updated.get('restore_error') is not None
    assert 'chown' in updated.get('restore_error')


def test_missing_backup_marks_error(tmp_path):
    db = DatabaseManager(db_path=tmp_path / 'r3.db')
    f = tmp_path / 'z.txt'
    f.write_text('q')

    undo = UndoManager(db=db, backup_dir=tmp_path / 'backups')
    item = CleanableItem(path=str(f), size=1, description='t', safety=SafetyLevel.SAFE)
    op_id = undo.log_operation('plug', [item])

    ui = undo.get_undo_items(op_id)[0]
    backup = Path(ui['backup_path'])
    assert backup.exists()
    # remove the backup file to simulate missing backup
    backup.unlink()
    res = undo.restore_operation(op_id)
    assert ui['id'] in res
    assert res[ui['id']] is False
    updated = db.get_undo_items(op_id)[0]
    assert updated.get('restored') in (0, None)
    assert 'backup missing' in (updated.get('restore_error') or '')