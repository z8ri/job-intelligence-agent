"""Bounded, on-demand verification of ranked candidates.

Candidates are checked in rank order, only until enough survive (`target_kept`) or a
budget runs out. Each call to the model is bounded (max calls, max candidates,
deadline, workers) and a run of consecutive failures stops the search instead of
burning the budget. A run that ends before it is done reports `partial` with the
reasons rather than pretending to be complete.

Judgements are cached per (content_hash, condition_id, model, prompt version):
  * unchanged job text + unchanged condition value => no new call;
  * flipping a condition hard/soft reuses the cache (strength is not part of the key);
  * new or edited conditions only send the missing ids;
  * a job whose text changed has a new content hash, so it is judged afresh.
Identical concurrent judgements share one in-flight call (`SingleFlight`).
Unverified/malformed answers are never cached.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from src.agent.evidence import JUDGE_PROMPT_VERSION, CompleteFn, JobJudgment, Judgment, judge_job
from src.agent.models import ConditionSet
from src.agent.retrieval import Candidate
from src.agent.snapshots import Snapshot
from src.llm import MODEL


@dataclass(frozen=True)
class Budget:
    target_kept: int = 10
    max_candidates: int = 30
    max_llm_calls: int = 30
    deadline_s: float = 60.0
    max_workers: int = 4
    max_consecutive_failures: int = 3


class JudgmentCache:
    def __init__(self, path: str | Path = ":memory:"):
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS judgments ("
                " content_hash TEXT NOT NULL, condition_id TEXT NOT NULL, model TEXT NOT NULL,"
                " prompt_version TEXT NOT NULL, judgment TEXT NOT NULL,"
                " PRIMARY KEY (content_hash, condition_id, model, prompt_version))"
            )

    def get_many(self, content_hash: str, condition_ids: list[str], model: str, prompt_version: str) -> dict[str, Judgment]:
        found: dict[str, Judgment] = {}
        with self._lock:
            for cid in condition_ids:
                row = self._conn.execute(
                    "SELECT judgment FROM judgments WHERE content_hash=? AND condition_id=? AND model=? AND prompt_version=?",
                    (content_hash, cid, model, prompt_version),
                ).fetchone()
                if row:
                    found[cid] = Judgment.model_validate_json(row[0])
        return found

    def put_many(self, content_hash: str, judgments: dict[str, Judgment], model: str, prompt_version: str) -> int:
        rows = [
            (content_hash, cid, model, prompt_version, j.model_dump_json())
            for cid, j in judgments.items()
            if not j.downgraded  # unverified / malformed answers are retried next time, not remembered
        ]
        with self._lock:
            self._conn.executemany("INSERT OR REPLACE INTO judgments VALUES (?,?,?,?,?)", rows)
            self._conn.commit()
        return len(rows)

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM judgments").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class _Call:
    def __init__(self):
        self.event = threading.Event()
        self.result = None
        self.error: BaseException | None = None


class SingleFlight:
    """Concurrent callers with the same key share one execution of `fn`."""

    def __init__(self):
        self._lock = threading.Lock()
        self._inflight: dict = {}

    def do(self, key, fn):
        with self._lock:
            call = self._inflight.get(key)
            leader = call is None
            if leader:
                call = self._inflight[key] = _Call()
        if leader:
            try:
                call.result = fn()
            except BaseException as e:  # propagate to followers too
                call.error = e
            finally:
                with self._lock:
                    del self._inflight[key]
                call.event.set()
        else:
            call.event.wait()
        if call.error is not None:
            raise call.error
        return call.result, leader


Status = Literal["kept", "excluded", "unverified"]


@dataclass
class VerifiedJob:
    candidate: Candidate
    status: Status
    judgment: JobJudgment | None = None
    conflicts: list[Judgment] = field(default_factory=list)  # verified hard conflicts (why excluded)
    unconfirmed_hard: list[str] = field(default_factory=list)  # hard conditions with no evidence either way
    note: str = ""


@dataclass
class VerificationResult:
    kept: list[VerifiedJob]
    excluded: list[VerifiedJob]
    unverified: list[VerifiedJob]
    status: Literal["complete", "partial"]
    reasons: list[str]
    stats: dict


class Verifier:
    def __init__(
        self,
        cache: JudgmentCache,
        *,
        complete: CompleteFn | None = None,
        model: str = MODEL,
        prompt_version: str = JUDGE_PROMPT_VERSION,
        flight: SingleFlight | None = None,
        clock: Callable[[], float] = time.monotonic,
        run_id: str | None = None,
    ):
        self.cache = cache
        self.complete = complete
        self.model = model
        self.prompt_version = prompt_version
        self.flight = flight or SingleFlight()
        self.clock = clock
        self.run_id = run_id

    def _judge_missing(self, snap: Snapshot, conditions: ConditionSet, missing: list[str]) -> tuple[dict[str, Judgment], bool]:
        key = (snap.content_hash, tuple(sorted(missing)), self.model, self.prompt_version)

        def call() -> dict[str, Judgment]:
            jj = judge_job(snap, conditions, only=missing, complete=self.complete, run_id=self.run_id)
            self.cache.put_many(snap.content_hash, jj.judgments, self.model, self.prompt_version)
            return jj.judgments

        return self.flight.do(key, call)

    def _classify(self, cand: Candidate, snap: Snapshot, conditions: ConditionSet, judgments: dict[str, Judgment]) -> VerifiedJob:
        jj = JobJudgment(
            job_key=snap.job_key, content_hash=snap.content_hash, condition_version=conditions.version, judgments=judgments
        )
        conflicts = jj.hard_conflicts(conditions)
        unconfirmed = [c.id for c in conditions.hard() if jj.verdict(c.id) == "unknown"]
        return VerifiedJob(cand, "excluded" if conflicts else "kept", jj, conflicts, unconfirmed)

    def verify(
        self,
        candidates: list[Candidate],
        get_snapshot: Callable[[str], Snapshot],
        conditions: ConditionSet,
        budget: Budget | None = None,
    ) -> VerificationResult:
        b = budget or Budget()
        start = self.clock()
        deadline = start + b.deadline_s
        kept: list[VerifiedJob] = []
        excluded: list[VerifiedJob] = []
        unverified: list[VerifiedJob] = []
        reasons: list[str] = []
        stats = {"llm_calls": 0, "shared_calls": 0, "cache_hits": 0, "failures": 0, "checked": 0}
        consecutive_failures = 0
        calls_used = 0
        idx = 0
        limit = min(len(candidates), b.max_candidates)
        all_ids = [c.id for c in conditions.conditions]
        stopped = False

        pool = ThreadPoolExecutor(max_workers=b.max_workers)
        try:
            while len(kept) < b.target_kept and idx < limit and not stopped:
                if self.clock() >= deadline:
                    reasons.append("deadline reached")
                    break
                # batch size is bounded by workers so a failing upstream wastes at most one batch of calls
                batch = candidates[idx : idx + max(1, min(b.target_kept - len(kept), limit - idx, b.max_workers))]
                idx += len(batch)

                pending: list[tuple[Candidate, Snapshot, dict[str, Judgment], list[str]]] = []
                for cand in batch:
                    snap = get_snapshot(cand.job_key)
                    cached = self.cache.get_many(snap.content_hash, all_ids, self.model, self.prompt_version)
                    stats["cache_hits"] += len(cached)
                    pending.append((cand, snap, cached, [i for i in all_ids if i not in cached]))

                futures = {}
                for cand, snap, cached, missing in pending:
                    if not missing:
                        continue
                    if calls_used >= b.max_llm_calls:
                        continue
                    calls_used += 1
                    futures[cand.job_key] = pool.submit(self._judge_missing, snap, conditions, missing)

                if futures:
                    wait(list(futures.values()), timeout=max(0.0, deadline - self.clock()))

                for cand, snap, cached, missing in pending:
                    fut = futures.get(cand.job_key)
                    fresh: dict[str, Judgment] = {}
                    if missing and fut is None:
                        unverified.append(VerifiedJob(cand, "unverified", note="llm call budget exhausted"))
                        stopped = True
                        if "llm call budget exhausted" not in reasons:
                            reasons.append("llm call budget exhausted")
                        continue
                    if fut is not None:
                        if not fut.done():
                            fut.cancel()
                            unverified.append(VerifiedJob(cand, "unverified", note="timed out"))
                            stopped = True
                            if "deadline reached" not in reasons:
                                reasons.append("deadline reached")
                            continue
                        try:
                            fresh, leader = fut.result()
                            stats["llm_calls" if leader else "shared_calls"] += 1
                            consecutive_failures = 0
                        except Exception as e:
                            stats["failures"] += 1
                            consecutive_failures += 1
                            unverified.append(VerifiedJob(cand, "unverified", note=f"judge failed: {e}"))
                            if consecutive_failures >= b.max_consecutive_failures:
                                stopped = True
                                if "too many consecutive failures" not in reasons:
                                    reasons.append("too many consecutive failures")
                            continue
                    stats["checked"] += 1
                    vj = self._classify(cand, snap, conditions, {**cached, **fresh})
                    (excluded if vj.status == "excluded" else kept).append(vj)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        if len(kept) < b.target_kept and not reasons and idx < len(candidates):
            reasons.append("max_candidates reached")
        for cand in candidates[idx:]:
            unverified.append(VerifiedJob(cand, "unverified", note="not checked"))

        kept = kept[: b.target_kept] if len(kept) > b.target_kept else kept
        stats["elapsed_s"] = round(self.clock() - start, 3)
        return VerificationResult(
            kept=kept,
            excluded=excluded,
            unverified=unverified,
            status="partial" if reasons else "complete",
            reasons=reasons,
            stats=stats,
        )
