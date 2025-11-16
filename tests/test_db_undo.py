from pathlib import Path
import tempfile

from smartcleaner.db.operations import DatabaseManager
from smartcleaner.managers.undo_manager import UndoManager
from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel


def test_db_log_and_undo_items_tmpfile(tmp_path):
    # Use a temporary sqlite file to test persistence
    db_path = tmp_path / 'test.db'
    db = DatabaseManager(db_path=db_path)

    # create a small temporary file to simulate a file being cleaned
    tmpfile = tmp_path / 'foo.txt'
    tmpfile.write_text('hello')

    undo = UndoManager(db=db, backup_dir=tmp_path / 'backups')

    item = CleanableItem(path=str(tmpfile), size=5, description='tmp', safety=SafetyLevel.SAFE)
    op_id = undo.log_operation('test_plugin', [item])

    assert op_id > 0

    undo_items = undo.get_undo_items(op_id)
    assert len(undo_items) == 1
    ui = undo_items[0]
    assert ui['item_path'] == str(tmpfile)
    # backup_path may be set and the original file should no longer exist
    if ui['backup_path']:
        assert not Path(ui['item_path']).exists()
        assert Path(ui['backup_path']).exists()
    else:
        # If backup wasn't possible, ensure can_restore is false
        assert ui['can_restore'] == 0
