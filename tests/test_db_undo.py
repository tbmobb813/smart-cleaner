from pathlib import Path

from smartcleaner.db.operations import DatabaseManager
from smartcleaner.managers.cleaner_manager import CleanableItem, SafetyLevel
from smartcleaner.managers.undo_manager import UndoManager


def test_db_log_and_undo_items_tmpfile(tmp_path):
    # Use a temporary sqlite file to test persistence
    db_path = tmp_path / "test.db"
    db = DatabaseManager(db_path=db_path)

    # create a small temporary file to simulate a file being cleaned
    tmpfile = tmp_path / "foo.txt"
    tmpfile.write_text("hello")
    # capture ownership before backup
    try:
        tmp_stat = tmpfile.stat()
        expected_uid = tmp_stat.st_uid
        expected_gid = tmp_stat.st_gid
    except Exception:
        expected_uid = None
        expected_gid = None

    undo = UndoManager(db=db, backup_dir=tmp_path / "backups")

    item = CleanableItem(path=str(tmpfile), size=5, description="tmp", safety=SafetyLevel.SAFE)
    op_id = undo.log_operation("test_plugin", [item])

    assert op_id > 0

    undo_items = undo.get_undo_items(op_id)
    assert len(undo_items) == 1
    ui = undo_items[0]
    assert ui["item_path"] == str(tmpfile)
    # backup_path may be set and the original file should no longer exist
    if ui["backup_path"]:
        assert not Path(ui["item_path"]).exists()
        assert Path(ui["backup_path"]).exists()
        # ownership should have been recorded
        assert ui.get("backup_uid") == expected_uid
        assert ui.get("backup_gid") == expected_gid
    else:
        # If backup wasn't possible, ensure can_restore is false
        assert ui["can_restore"] == 0


def test_undo_restore_roundtrip(tmp_path):
    db_path = tmp_path / "test2.db"
    db = DatabaseManager(db_path=db_path)

    # create a small temporary file to simulate a file being cleaned
    tmpfile = tmp_path / "bar.txt"
    content = "goodbye"
    tmpfile.write_text(content)
    try:
        tmp_stat = tmpfile.stat()
        expected_uid = tmp_stat.st_uid
        expected_gid = tmp_stat.st_gid
    except Exception:
        expected_uid = None
        expected_gid = None

    undo = UndoManager(db=db, backup_dir=tmp_path / "backups")

    item = CleanableItem(path=str(tmpfile), size=len(content), description="tmp", safety=SafetyLevel.SAFE)
    op_id = undo.log_operation("test_plugin", [item])

    undo_items = undo.get_undo_items(op_id)
    assert len(undo_items) == 1
    ui = undo_items[0]

    # If backup occurred, restore should move file back
    if ui["backup_path"]:
        # ensure original does not exist now
        assert not Path(ui["item_path"]).exists()
        res = undo.restore_operation(op_id)
        # map contains entry for undo log id
        assert ui["id"] in res
        assert res[ui["id"]] is True
        # original should be back with same contents
        assert Path(ui["item_path"]).exists()
        assert Path(ui["item_path"]).read_text() == content
        # backup should no longer exist
        assert not Path(ui["backup_path"]).exists()
        # DB should record restored status
        updated = db.get_undo_items(op_id)[0]
        assert updated.get("restored") == 1
        assert updated.get("restored_timestamp") is not None
        assert updated.get("restore_error") is None
    else:
        # nothing to restore
        res = undo.restore_operation(op_id)
        assert all(not v for v in res.values())
        updated = db.get_undo_items(op_id)[0]
        # restored should be false/0 and no timestamp
        assert updated.get("restored") in (0, None)
        assert updated.get("restored_timestamp") is None
        # ensure ownership recorded
        assert ui.get("backup_uid") == expected_uid
        assert ui.get("backup_gid") == expected_gid


def test_restore_conflict_renames(tmp_path):
    db_path = tmp_path / "test3.db"
    db = DatabaseManager(db_path=db_path)

    # create original file and record it (log_operation will move it to backup)
    orig = tmp_path / "conflict.txt"
    orig_content = "original"
    orig.write_text(orig_content)
    try:
        orig_stat = orig.stat()
        expected_uid = orig_stat.st_uid
        expected_gid = orig_stat.st_gid
    except Exception:
        expected_uid = None
        expected_gid = None

    undo = UndoManager(db=db, backup_dir=tmp_path / "backups")

    item = CleanableItem(path=str(orig), size=len(orig_content), description="tmp", safety=SafetyLevel.SAFE)
    op_id = undo.log_operation("test_plugin", [item])

    undo_items = undo.get_undo_items(op_id)
    assert len(undo_items) == 1
    ui = undo_items[0]

    # create a new file at the original path to simulate a conflict
    new_content = "new-file-here"
    Path(ui["item_path"]).write_text(new_content)

    # monkeypatch os.chown to capture calls (we're likely not root in tests)
    import os as _os

    real_chown = _os.chown
    chown_called = {}

    def fake_chown(path, uid, gid):
        chown_called["args"] = (path, uid, gid)

    _os.chown = fake_chown
    try:
        res = undo.restore_operation(op_id)
    finally:
        _os.chown = real_chown
    assert ui["id"] in res
    assert res[ui["id"]] is True

    # restored file should contain the original content
    assert Path(ui["item_path"]).read_text() == orig_content

    # DB should have recorded backup uid/gid
    assert ui.get("backup_uid") == expected_uid
    assert ui.get("backup_gid") == expected_gid

    # chown should have been attempted with recorded uid/gid
    assert "args" in chown_called
    ch_path, ch_uid, ch_gid = chown_called["args"]
    assert Path(ch_path).exists()
    assert ch_uid == expected_uid
    assert ch_gid == expected_gid

    # the conflicting file should have been renamed to .orig.<ts>
    parent = Path(ui["item_path"]).parent
    base = Path(ui["item_path"]).name
    matches = [p for p in parent.iterdir() if p.name.startswith(f"{base}.orig.")]
    assert len(matches) == 1
    assert matches[0].read_text() == new_content
