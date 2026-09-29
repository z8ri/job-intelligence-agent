"""SQLite record of search tasks and their per-condition-version runs.

A task is one user request. Every time its conditions change (a version bump) a new
run is stored beside the old one, so a result is always bound to the exact
condition version that produced it and earlier versions stay readable.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TaskStore:
    def __init__(self, path: str | Path = ":memory:"):
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY, query TEXT NOT NULL,
                    latest_version INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs (
                    task_id TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, version));
                """
            )

    def create_task(self, query: str) -> str:
        task_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._conn.execute("INSERT INTO tasks (task_id, query, created_at) VALUES (?,?,?)", (task_id, query, _now()))
            self._conn.commit()
        return task_id

    def exists(self, task_id: str) -> bool:
        with self._lock:
            return self._conn.execute("SELECT 1 FROM tasks WHERE task_id=?", (task_id,)).fetchone() is not None

    def save_run(self, task_id: str, version: int, status: str, payload: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO runs (task_id, version, status, payload, created_at) VALUES (?,?,?,?,?)",
                (task_id, version, status, json.dumps(payload, ensure_ascii=False), _now()),
            )
            self._conn.execute(
                "UPDATE tasks SET latest_version=MAX(latest_version, ?) WHERE task_id=?", (version, task_id)
            )
            self._conn.commit()

    def latest_version(self, task_id: str) -> int | None:
        with self._lock:
            row = self._conn.execute("SELECT latest_version FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        return row[0] if row and row[0] else None

    def get_run(self, task_id: str, version: int | None = None) -> dict | None:
        version = version if version is not None else self.latest_version(task_id)
        if version is None:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM runs WHERE task_id=? AND version=?", (task_id, version)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def versions(self, task_id: str) -> list[int]:
        with self._lock:
            rows = self._conn.execute("SELECT version FROM runs WHERE task_id=? ORDER BY version", (task_id,)).fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
