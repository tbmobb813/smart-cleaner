from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import shutil
import os

from ..db.operations import DatabaseManager
from .cleaner_manager import CleanableItem


class UndoManager:
    """Minimal undo manager that records operations and optionally backs up files.

    For file deletions, it attempts to move files to a backup directory and records
    the backup path in the DB. For non-file operations (packages), it records
    metadata that can be used to attempt a restore.
    """

    def __init__(self, db: Optional[DatabaseManager] = None, backup_dir: Optional[Path] = None):
        self.db = db or DatabaseManager()
        self.backup_dir = backup_dir or Path.home() / '.local' / 'share' / 'smartcleaner' / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def log_operation(self, plugin_name: str, items: List[CleanableItem]) -> int:
        """Log an operation and create backup entries for file items.

        Returns the operation_id in the DB.
        """
        # Log the clean operation summary
        total_size = sum(item.size for item in items)
        op_id = self.db.log_clean_operation(plugin_name=plugin_name, items_count=len(items), size_freed=total_size, success=True)

        # For each item, if it looks like a path on disk, attempt to backup (move) it.
        for item in items:
            backup_path = None
            can_restore = False
            try:
                p = Path(item.path)
                if p.exists() and p.is_file():
                    # capture ownership before moving
                    try:
                        st = p.stat()
                        backup_uid = st.st_uid
                        backup_gid = st.st_gid
                    except Exception:
                        backup_uid = None
                        backup_gid = None

                    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                    dest_dir = self.backup_dir / f'op_{op_id}_{ts}'
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / p.name
                    shutil.move(str(p), str(dest))
                    backup_path = str(dest)
                    can_restore = True
            except Exception:
                # Non-fatal; record that we couldn't backup
                backup_path = None
                can_restore = False

            # store ownership info if available
            try:
                self.db.save_undo_item(operation_id=op_id, item_path=item.path, backup_path=backup_path, can_restore=can_restore, backup_uid=locals().get('backup_uid'), backup_gid=locals().get('backup_gid'))
            except Exception:
                # best-effort; ignore DB failures
                pass

        return op_id

    def get_undo_items(self, operation_id: int):
        return self.db.get_undo_items(operation_id)

    def prune_backups(self, keep_last: Optional[int] = None, older_than_days: Optional[int] = None) -> dict:
        """Prune backup directories in the backup_dir.

        - keep_last: keep this many most-recent operation directories (by timestamp in name)
        - older_than_days: remove backups older than this many days

        Returns a dict with counts: {'removed': n, 'remaining': m}
        """
        removed = 0
        dirs = [p for p in self.backup_dir.iterdir() if p.is_dir() and p.name.startswith('op_')]
        # parse timestamp suffix from name op_<id>_<ts>
        def parse_ts(p: Path):
            parts = p.name.split('_')
            try:
                ts = parts[-1]
                return datetime.strptime(ts, '%Y%m%d%H%M%S')
            except Exception:
                return datetime.min

        dirs_sorted = sorted(dirs, key=parse_ts, reverse=True)

        to_remove = set()
        if keep_last is not None and keep_last < len(dirs_sorted):
            for d in dirs_sorted[keep_last:]:
                to_remove.add(d)

        if older_than_days is not None:
            cutoff = datetime.utcnow() - timedelta(days=older_than_days)
            for d in dirs:
                if parse_ts(d) < cutoff:
                    to_remove.add(d)

        for d in to_remove:
            try:
                shutil.rmtree(d)
                removed += 1
            except Exception:
                pass

        remaining = len([p for p in self.backup_dir.iterdir() if p.is_dir() and p.name.startswith('op_')])
        return {'removed': removed, 'remaining': remaining}

    def restore_operation(self, operation_id: int, conflict_policy: str = 'rename') -> dict:
        """Attempt to restore all items for a given operation.

        Returns a mapping of undo_log id -> bool indicating whether the item
        was successfully restored.
        """
        results = {}
        items = self.get_undo_items(operation_id)
        for it in items:
            uid = it.get('id')
            backup = it.get('backup_path')
            original = it.get('item_path')
            can_restore = bool(it.get('can_restore'))
            success = False
            err = None
            if can_restore and backup:
                b = Path(backup)
                dest = Path(original)
                try:
                    if not b.exists():
                        raise FileNotFoundError(f"backup missing: {b}")

                    # Handle existing destination according to conflict_policy
                    if dest.exists():
                        if conflict_policy == 'rename':
                            ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                            renamed = dest.parent / f"{dest.name}.orig.{ts}"
                            dest.rename(renamed)
                        elif conflict_policy == 'overwrite':
                            # remove existing file/dir
                            if dest.is_dir():
                                shutil.rmtree(dest)
                            else:
                                dest.unlink()
                        elif conflict_policy == 'skip':
                            # skip restoring this item
                            success = False
                            err = 'skipped due to existing destination'
                            # record and continue
                            try:
                                self.db.mark_undo_restored(uid, False, err)
                            except Exception:
                                pass
                            results[uid] = False
                            continue
                        else:
                            raise ValueError(f'unknown conflict policy: {conflict_policy}')

                    dest.parent.mkdir(parents=True, exist_ok=True)

                    # Try move first (preserves metadata). If it fails (cross-fs), fall back to copy2 + remove.
                    try:
                        shutil.move(str(b), str(dest))
                    except Exception as e_move:
                        # fallback: copy with metadata then try to remove backup
                        try:
                            shutil.copy2(str(b), str(dest))
                            try:
                                b.unlink()
                            except Exception:
                                # best-effort cleanup
                                pass
                        except Exception as e_copy:
                            raise Exception(f"move failed: {e_move}; copy failed: {e_copy}")

                    # Success if we reached here
                    success = True
                    # Attempt to restore ownership if recorded
                    try:
                        b_uid = it.get('backup_uid')
                        b_gid = it.get('backup_gid')
                        if b_uid is not None and b_gid is not None:
                            try:
                                os.chown(str(dest), int(b_uid), int(b_gid))
                            except Exception as e_chown:
                                # don't fail restore for chown issues; record error
                                if err:
                                    err = f"{err}; chown failed: {e_chown}"
                                else:
                                    err = f"chown failed: {e_chown}"
                    except Exception:
                        # defensive: ignore any issues reading UID/GID
                        pass
                except Exception as e:
                    err = str(e)
                    success = False

            # Record result in DB if supported (best-effort)
            try:
                self.db.mark_undo_restored(uid, success, err)
            except Exception:
                pass

            results[uid] = success

        return results
