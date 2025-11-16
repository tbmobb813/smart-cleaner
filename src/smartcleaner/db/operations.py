"""Minimal DatabaseManager using sqlite3 for logging operations and undo entries.

This intentionally avoids heavy ORMs to keep the dependency surface small for
the example. The manager exposes simple methods used by tests.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path: Optional[Path] = None):
        # Use in-memory DB when db_path is None for tests
        self._db_path = db_path
        self._conn = None
        self._ensure_conn()

    def _ensure_conn(self):
        if self._conn:
            return
        if self._db_path is None:
            self._conn = sqlite3.connect(':memory:')
        else:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cur = self._conn.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS clean_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            plugin_name TEXT NOT NULL,
            items_count INTEGER,
            size_freed INTEGER,
            success INTEGER,
            error_message TEXT
        )
        ''')

        cur.execute('''
        CREATE TABLE IF NOT EXISTS undo_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id INTEGER,
            item_path TEXT,
            backup_path TEXT,
            can_restore INTEGER,
            timestamp TEXT
        )
        ''')

        self._conn.commit()

    def log_clean_operation(self, plugin_name: str, items_count: int, size_freed: int, success: bool, error_message: Optional[str] = None) -> int:
        ts = datetime.utcnow().isoformat()
        cur = self._conn.cursor()
        cur.execute(
            'INSERT INTO clean_operations (timestamp, plugin_name, items_count, size_freed, success, error_message) VALUES (?, ?, ?, ?, ?, ?)',
            (ts, plugin_name, items_count, size_freed, int(success), error_message)
        )
        self._conn.commit()
        return cur.lastrowid

    def save_undo_item(self, operation_id: int, item_path: str, backup_path: Optional[str], can_restore: bool = True) -> int:
        ts = datetime.utcnow().isoformat()
        cur = self._conn.cursor()
        cur.execute(
            'INSERT INTO undo_log (operation_id, item_path, backup_path, can_restore, timestamp) VALUES (?, ?, ?, ?, ?)',
            (operation_id, item_path, backup_path, int(can_restore), ts)
        )
        self._conn.commit()
        return cur.lastrowid

    def get_recent_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM clean_operations ORDER BY id DESC LIMIT ?', (limit,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_undo_items(self, operation_id: int) -> List[Dict[str, Any]]:
        cur = self._conn.cursor()
        cur.execute('SELECT * FROM undo_log WHERE operation_id = ?', (operation_id,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
