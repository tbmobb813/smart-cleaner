from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from datetime import datetime
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

            self.db.save_undo_item(operation_id=op_id, item_path=item.path, backup_path=backup_path, can_restore=can_restore)

        return op_id

    def get_undo_items(self, operation_id: int):
        return self.db.get_undo_items(operation_id)
