"""Versioned, replayable job snapshots backed by SQLite.

A snapshot keeps the source, stable id, url, raw content, normalized text, fetch
time and a content hash. Storing the same content again only refreshes
`last_seen_at`; changed content becomes a new version, so old rankings can be
replayed against the exact text they saw (`as_of`).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field

from src.agent.segmentation import Segment, normalize_text, segment


def _utc_iso(value: str | datetime | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def canonical_url(url: str | None) -> str | None:
    """Normalized job link used for cross-source merging; None when there is no link."""
    if not url:
        return None
    parts = urlsplit(url.strip())
    if not parts.netloc:
        return None
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


class Snapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_key: str
    source: str
    source_job_id: str
    version: int = 0
    content_hash: str
    url: str | None = None
    title: str = ""
    company: str = ""
    location: str = ""
    fetched_at: str
    last_seen_at: str
    publish_time: str | None = None
    raw_content: str
    text: str
    hints: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        source: str,
        source_job_id: str,
        raw_content: str,
        title: str = "",
        company: str = "",
        location: str = "",
        url: str | None = None,
        fetched_at: str | datetime | None = None,
        publish_time: str | None = None,
        hints: dict[str, Any] | None = None,
    ) -> "Snapshot":
        """`hints` are scraper guesses (regex salary, remote flag, tags). They are
        kept for debugging only and are never treated as verified facts."""
        fetched = _utc_iso(fetched_at)
        digest = hashlib.sha256("\x1f".join([title, location, raw_content]).encode()).hexdigest()
        return cls(
            job_key=f"{source}:{source_job_id}",
            source=source,
            source_job_id=source_job_id,
            content_hash=digest,
            url=url,
            title=title,
            company=company,
            location=location,
            fetched_at=fetched,
            last_seen_at=fetched,
            publish_time=publish_time,
            raw_content=raw_content,
            text=normalize_text(raw_content),
            hints=hints or {},
        )

    def segments(self) -> list[Segment]:
        return segment(self.text)


class PutResult(BaseModel):
    snapshot: Snapshot
    is_new_version: bool
    previous_hash: str | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    job_key TEXT NOT NULL,
    version INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    source TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    url TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    fetched_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    publish_time TEXT,
    raw_content TEXT NOT NULL,
    text TEXT NOT NULL,
    hints TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (job_key, version)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_hash ON snapshots (job_key, content_hash);
CREATE INDEX IF NOT EXISTS idx_snapshots_fetched ON snapshots (fetched_at);
"""

_COLUMNS = (
    "job_key, version, content_hash, source, source_job_id, url, title, company, location, "
    "fetched_at, last_seen_at, publish_time, raw_content, text, hints"
)


def _row_to_snapshot(row: sqlite3.Row) -> Snapshot:
    data = dict(row)
    data["hints"] = json.loads(data["hints"] or "{}")
    return Snapshot(**data)


class SnapshotStore:
    def __init__(self, path: str | Path = ":memory:"):
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def put(self, snap: Snapshot) -> PutResult:
        with self._lock:
            cur = self._conn.execute(
                f"SELECT {_COLUMNS} FROM snapshots WHERE job_key=? ORDER BY version DESC LIMIT 1",
                (snap.job_key,),
            ).fetchone()
            if cur is not None and cur["content_hash"] == snap.content_hash:
                self._conn.execute(
                    "UPDATE snapshots SET last_seen_at=? WHERE job_key=? AND version=?",
                    (max(cur["last_seen_at"], snap.last_seen_at), snap.job_key, cur["version"]),
                )
                self._conn.commit()
                stored = self.latest(snap.job_key)
                return PutResult(snapshot=stored, is_new_version=False, previous_hash=cur["content_hash"])

            version = (cur["version"] + 1) if cur is not None else 1
            stored = snap.model_copy(update={"version": version})
            self._conn.execute(
                f"INSERT INTO snapshots ({_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    stored.job_key, stored.version, stored.content_hash, stored.source,
                    stored.source_job_id, stored.url, stored.title, stored.company, stored.location,
                    stored.fetched_at, stored.last_seen_at, stored.publish_time, stored.raw_content,
                    stored.text, json.dumps(stored.hints, ensure_ascii=False),
                ),
            )
            self._conn.commit()
            return PutResult(
                snapshot=stored,
                is_new_version=True,
                previous_hash=cur["content_hash"] if cur is not None else None,
            )

    def latest(self, job_key: str, as_of: str | datetime | None = None) -> Snapshot | None:
        sql = f"SELECT {_COLUMNS} FROM snapshots WHERE job_key=?"
        params: list[Any] = [job_key]
        if as_of is not None:
            sql += " AND fetched_at<=?"
            params.append(_utc_iso(as_of))
        sql += " ORDER BY version DESC LIMIT 1"
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
        return _row_to_snapshot(row) if row else None

    def history(self, job_key: str) -> list[Snapshot]:
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {_COLUMNS} FROM snapshots WHERE job_key=? ORDER BY version", (job_key,)
            ).fetchall()
        return [_row_to_snapshot(r) for r in rows]

    def all_latest(self, as_of: str | datetime | None = None) -> list[Snapshot]:
        """The newest version of every job (as of a timestamp, for replay), ordered by key."""
        cutoff = _utc_iso(as_of) if as_of is not None else None
        cond = "AND fetched_at<=?" if cutoff else ""
        sql = f"""
            SELECT {_COLUMNS} FROM snapshots s
            WHERE version = (SELECT MAX(version) FROM snapshots
                             WHERE job_key = s.job_key {cond})
            ORDER BY job_key
        """
        params = [cutoff] if cutoff else []
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_snapshot(r) for r in rows]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(DISTINCT job_key) FROM snapshots").fetchone()[0]


def merge_duplicates(snapshots: list[Snapshot]) -> tuple[list[Snapshot], dict[str, list[str]]]:
    """Merge snapshots only when they share an explicit canonical job link.

    Same company + same title is NOT enough (different cities or levels share
    both). Returns (representatives, {representative_key: [merged_keys]}); the
    representative is the most recently fetched one.
    """
    groups: dict[str, list[Snapshot]] = {}
    passthrough: list[Snapshot] = []
    for s in snapshots:
        url = canonical_url(s.url)
        if url is None:
            passthrough.append(s)
        else:
            groups.setdefault(url, []).append(s)

    reps: list[Snapshot] = list(passthrough)
    merged: dict[str, list[str]] = {}
    for members in groups.values():
        members.sort(key=lambda s: (s.fetched_at, s.job_key))
        rep = members[-1]
        reps.append(rep)
        others = [m.job_key for m in members if m.job_key != rep.job_key]
        if others:
            merged[rep.job_key] = others
    reps.sort(key=lambda s: s.job_key)
    return reps, merged


def import_legacy_json(path: str | Path, store: SnapshotStore, fetched_at: str | datetime | None = None) -> int:
    """Load the legacy structured_jobs.json into the store. The legacy salary/remote/tags
    fields come from regex scrapers, so they go into `hints`, not into facts."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    when = fetched_at or datetime.fromtimestamp(Path(path).stat().st_mtime, tz=timezone.utc)
    for rec in records:
        legacy_id = str(rec["job_id"])
        source_job_id = legacy_id.split("_", 1)[1] if "_" in legacy_id else legacy_id
        store.put(
            Snapshot.create(
                source=rec.get("source", "unknown"),
                source_job_id=source_job_id,
                raw_content=rec.get("description") or "",
                title=rec.get("title") or "",
                company=rec.get("company") or "",
                location=rec.get("location") or "",
                url=rec.get("url"),
                fetched_at=when,
                publish_time=rec.get("publish_time"),
                hints={
                    "legacy_job_id": legacy_id,
                    "remote": rec.get("remote"),
                    "salary_min": rec.get("salary_min"),
                    "salary_max": rec.get("salary_max"),
                    "tags": rec.get("tags") or [],
                },
            )
        )
    return len(records)
