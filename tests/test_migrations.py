import sqlite3

from smartcleaner.db.operations import DatabaseManager, CURRENT_SCHEMA_VERSION


def test_migration_from_old_schema(tmp_path):
    # create a DB with no schema_version table to simulate old DB
    db_path = tmp_path / 'old.db'
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    # create only the clean_operations table to simulate very old schema
    cur.execute('''
    CREATE TABLE clean_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        plugin_name TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

    # Now open via DatabaseManager - it should add schema tables and migrate
    dbm = DatabaseManager(db_path=db_path)
    assert dbm.get_schema_version() == CURRENT_SCHEMA_VERSION
