from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @property
    def path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    department_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    department_id TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    original_filename TEXT DEFAULT '',
                    stored_filename TEXT DEFAULT '',
                    storage_path TEXT DEFAULT '',
                    content_type TEXT DEFAULT '',
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    checksum TEXT DEFAULT '',
                    uploaded_at TEXT NOT NULL,
                    indexing_status TEXT NOT NULL DEFAULT 'pending',
                    last_indexed_at TEXT,
                    metadata_json TEXT DEFAULT '{}',
                    versions_json TEXT DEFAULT '[]'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingest_jobs (
                    job_id TEXT PRIMARY KEY,
                    document_id TEXT,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    indexed_files INTEGER NOT NULL DEFAULT 0,
                    indexed_chunks INTEGER NOT NULL DEFAULT 0,
                    removed_files INTEGER NOT NULL DEFAULT 0,
                    reused_existing_index INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT
                )
                """
            )


def dumps_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads_json(value: str | None, default: object) -> object:
    if not value:
        return default
    return json.loads(value)
