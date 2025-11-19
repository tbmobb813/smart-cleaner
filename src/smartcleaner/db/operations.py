"""Minimal DatabaseManager using sqlite3 for logging operations and undo entries.

This intentionally avoids heavy ORMs to keep the dependency surface small for
the example. The manager exposes simple methods used by tests.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, cast

# bump this when schema changes are added via migrations
CURRENT_SCHEMA_VERSION = 2


class DatabaseManager:
    def __init__(self, db_path: Path | None = None):
        # Use in-memory DB when db_path is None for tests
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._ensure_conn()

    def _ensure_conn(self):
        if self._conn:
            return
        if self._db_path is None:
            self._conn = sqlite3.connect(":memory:")
        else:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS clean_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            plugin_name TEXT NOT NULL,
            items_count INTEGER,
            size_freed INTEGER,
            success INTEGER,
            error_message TEXT
        )
        """
        )

        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS undo_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER,
            item_path TEXT,
            backup_path TEXT,
            can_restore INTEGER,
            timestamp TEXT,
            restored INTEGER DEFAULT 0,
            restored_timestamp TEXT,
            restore_error TEXT,
            backup_uid INTEGER,
            backup_gid INTEGER
        )
        """
        )

        self._conn.commit()
        # Create schema versioning table and apply migrations as needed
        self._create_schema_table()
        self._apply_migrations()

    def _create_schema_table(self):
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER,
            updated TEXT
        )
        """
        )
        self._conn.commit()
        # Ensure at least one row exists
        cur.execute("SELECT COUNT(*) as c FROM schema_version")
        row = cur.fetchone()
        if row and row["c"] == 0:
            cur.execute(
                "INSERT INTO schema_version (version, updated) VALUES (?, ?)", (0, datetime.utcnow().isoformat())
            )
            self._conn.commit()

    def _get_schema_version(self) -> int:
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute("SELECT version FROM schema_version LIMIT 1")
        row = cur.fetchone()
        return int(row["version"]) if row else 0

    def _set_schema_version(self, version: int):
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        sql = (
            "UPDATE schema_version SET version = ?, updated = ?"
        )
        cur.execute(sql, (int(version), datetime.utcnow().isoformat()))
        self._conn.commit()

    # Public API to get schema version
    def get_schema_version(self) -> int:
        return self._get_schema_version()

    def _apply_migrations(self):
        """Apply incremental migrations to bring DB to CURRENT_SCHEMA_VERSION."""
        cur_ver = self._get_schema_version()
        if cur_ver >= CURRENT_SCHEMA_VERSION:
            return
        # apply migrations sequentially
        for v in range(cur_ver + 1, CURRENT_SCHEMA_VERSION + 1):
            if v == 1:
                # initial schema created in _create_tables; nothing to do
                pass
            if v == 2:
                # ensure undo_log has the newer columns
                self._ensure_undo_columns()
            # mark migration applied
            self._set_schema_version(v)

    def get_pending_migrations(self) -> list:
        """Return a list of schema versions that would be applied to upgrade the DB."""
        cur_ver = self._get_schema_version()
        return [v for v in range(cur_ver + 1, CURRENT_SCHEMA_VERSION + 1)]

    def apply_migrations(self) -> list:
        """Apply pending migrations and return list of applied versions."""
        pending = self.get_pending_migrations()
        if not pending:
            return []
        # call internal applier which also updates version
        self._apply_migrations()
        return pending

    def _ensure_undo_columns(self):
        """Add missing undo_log columns for older DBs (no-op when present)."""
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute("PRAGMA table_info(undo_log)")
        cols = {row["name"] for row in cur.fetchall()}
        alters = []
        if "restored" not in cols:
            alters.append("ALTER TABLE undo_log ADD COLUMN restored INTEGER DEFAULT 0")
        if "restored_timestamp" not in cols:
            alters.append("ALTER TABLE undo_log ADD COLUMN restored_timestamp TEXT")
        if "restore_error" not in cols:
            alters.append("ALTER TABLE undo_log ADD COLUMN restore_error TEXT")
        if "backup_uid" not in cols:
            alters.append("ALTER TABLE undo_log ADD COLUMN backup_uid INTEGER")
        if "backup_gid" not in cols:
            alters.append("ALTER TABLE undo_log ADD COLUMN backup_gid INTEGER")

        for a in alters:
            try:
                cur.execute(a)
            except Exception:
                # best-effort; ignore failures for incompatible older schemas
                pass
        if alters:
            self._conn.commit()

    def log_clean_operation(
        self, plugin_name: str, items_count: int, size_freed: int, success: bool, error_message: str | None = None
    ) -> int:
        ts = datetime.utcnow().isoformat()
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        sql = (
            "INSERT INTO clean_operations (timestamp, plugin_name, items_count, size_freed, success, error_message) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        cur.execute(sql, (ts, plugin_name, items_count, size_freed, int(success), error_message))
        self._conn.commit()
        # cur.lastrowid is usually an int after INSERT; cast for typing safety
        return cast(int, cur.lastrowid)

    def save_undo_item(
        self,
        operation_id: int,
        item_path: str,
        backup_path: str | None,
        can_restore: bool = True,
        backup_uid: int | None = None,
        backup_gid: int | None = None,
    ) -> int:
        ts = datetime.utcnow().isoformat()
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        sql = (
            "INSERT INTO undo_log (operation_id, item_path, backup_path, can_restore, "
            "timestamp, backup_uid, backup_gid) VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        cur.execute(sql, (operation_id, item_path, backup_path, int(can_restore), ts, backup_uid, backup_gid))
        self._conn.commit()
        return cast(int, cur.lastrowid)

    def mark_undo_restored(self, undo_id: int, success: bool, error_message: str | None = None) -> None:
        ts = datetime.utcnow().isoformat() if success else None
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        sql = (
            "UPDATE undo_log SET restored = ?, restored_timestamp = ?, restore_error = ? "
            "WHERE id = ?"
        )
        cur.execute(sql, (int(success), ts, error_message, undo_id))
        self._conn.commit()

    def get_recent_operations(self, limit: int = 10) -> list[dict[str, Any]]:
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM clean_operations ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_undo_items(self, operation_id: int) -> list[dict[str, Any]]:
        self._ensure_conn()
        assert self._conn is not None
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM undo_log WHERE operation_id = ?", (operation_id,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
