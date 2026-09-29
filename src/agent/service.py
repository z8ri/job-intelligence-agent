"""Search orchestration: parse -> retrieve -> rerank -> verify, bound to a condition version.

Result statuses:
  complete  every stage ran and the verification budget was not the limit
  partial   usable results, but something degraded (see `reasons`): a retrieval channel or
            the reranker was unavailable, or verification stopped on a budget/deadline
  clarify   the conditions contain an ambiguity that changes which jobs qualify; nothing
            was searched until the caller confirms with `run`/`revise`
  failed    no usable result (unparseable request, empty index, retrieval error)
"""

from __future__ import annotations

import time
from typing import Callable

from src.agent.conditions import ConditionParseError, parse_conditions
from src.agent.explain import explain_rank_changes
from src.agent.graph import build_search_graph
from src.agent.models import ConditionSet
from src.agent.rerank import Scorer
from src.agent.retrieval import JobIndex
from src.agent.scoring import soft_breakdown, soft_score, to_confirm
from src.agent.tasks import TaskStore
from src.agent.verification import Budget, SingleFlight, VerifiedJob, Verifier


class TaskNotFound(KeyError):
    pass


class VersionConflict(RuntimeError):
    def __init__(self, current: int, expected: int):
        super().__init__(f"conditions are at version {current}, request was for {expected}")
        self.current = current
        self.expected = expected


class InvalidRevision(ValueError):
    pass


def _judgment_view(j) -> dict:
    return {"verdict": j.verdict, "quote": j.quote, "span": list(j.span) if j.span else None,
            "reason": j.reason, "downgraded": j.downgraded}


class SearchService:
    def __init__(
        self,
        index: JobIndex,
        scorer: Scorer | None,
        verifier: Verifier,
        store: TaskStore,
        *,
        parse: Callable[[str], ConditionSet] = parse_conditions,
        budget: Budget | None = None,
        retrieve_top_n: int = 50,
        rerank_depth: int = 30,
        max_retries: int = 1,
    ):
        self.index = index
        self.scorer = scorer
        self.verifier = verifier
        self.store = store
        self.parse = parse
        self.budget = budget or Budget()
        self.retrieve_top_n = retrieve_top_n
        self.rerank_depth = rerank_depth
        self.max_retries = max_retries
        self._flight = SingleFlight()
        self._graph = build_search_graph(index, scorer, verifier, retrieve_top_n=retrieve_top_n, rerank_depth=rerank_depth)

    # ---- public operations -------------------------------------------------

    def start(self, query: str, *, proceed: bool = False) -> dict:
        task_id = self.store.create_task(query)
        try:
            conditions = self.parse(query)
        except ConditionParseError as e:
            return self._store(task_id, 1, self._envelope("failed", None, reasons=[f"could not parse request: {e}"]))
        except Exception as e:
            return self._store(task_id, 1, self._envelope("failed", None, reasons=[f"condition parsing unavailable: {e}"]))
        if not conditions.conditions or (conditions.clarifications and not proceed):
            return self._store(task_id, conditions.version, self._envelope("clarify", conditions))
        return self._run(task_id, conditions)

    def get(self, task_id: str, version: int | None = None) -> dict:
        self._require(task_id)
        run = self.store.get_run(task_id, version)
        if run is None:
            raise TaskNotFound(f"{task_id} has no version {version}")
        return {**run, "versions": self.store.versions(task_id)}

    def run(self, task_id: str, expected_version: int) -> dict:
        """Run the current conditions (used to confirm a `clarify` state). Idempotent once a
        result exists for this version."""
        current = self._current(task_id, expected_version)
        if current["status"] not in ("clarify", "failed") or current["conditions"] is None:
            return self.get(task_id, expected_version)
        cs = ConditionSet.model_validate(current["conditions"])
        if not cs.conditions:
            return self.get(task_id, expected_version)
        return self._run(task_id, cs)

    def revise(
        self,
        task_id: str,
        expected_version: int,
        *,
        strengths: dict[str, str] | None = None,
        remove: list[str] | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict:
        current = self._current(task_id, expected_version)
        if current["conditions"] is None:
            raise InvalidRevision("this task has no parsed conditions to revise")
        cs = ConditionSet.model_validate(current["conditions"])
        strengths, remove, weights = strengths or {}, remove or [], weights or {}
        unknown = [i for i in [*strengths, *remove, *weights] if cs.get(i) is None]
        if unknown:
            raise InvalidRevision(f"unknown condition ids: {unknown}")
        if any(s not in ("hard", "soft") for s in strengths.values()):
            raise InvalidRevision("strength must be 'hard' or 'soft'")
        if any(not isinstance(w, (int, float)) or not 0.05 <= w <= 1.0 for w in weights.values()):
            raise InvalidRevision("weight must be a number between 0.05 and 1.0")
        conditions = []
        for c in cs.conditions:
            if c.id in remove:
                continue
            update = {"strength": strengths.get(c.id, c.strength)}
            if c.id in weights:
                if update["strength"] != "soft":
                    raise InvalidRevision(f"only soft conditions take a weight: {c.id}")
                update["weight"] = float(weights[c.id])
            conditions.append(c.model_copy(update=update))
        if not conditions:
            raise InvalidRevision("a request needs at least one condition")
        revised, changes = cs.revise(cs.raw_query, conditions, cs.clarifications)
        if changes.is_empty and current["status"] != "clarify":
            return self.get(task_id, expected_version)
        return self._run(task_id, revised, changes={"added": changes.added, "removed": changes.removed,
                                                    "modified": changes.modified}, previous=current)

    # ---- internals ----------------------------------------------------------

    def _require(self, task_id: str) -> None:
        if not self.store.exists(task_id):
            raise TaskNotFound(task_id)

    def _current(self, task_id: str, expected_version: int) -> dict:
        self._require(task_id)
        latest = self.store.latest_version(task_id)
        if latest is None or latest != expected_version:
            raise VersionConflict(latest or 0, expected_version)
        return self.store.get_run(task_id, latest)

    def _store(self, task_id: str, version: int, envelope: dict) -> dict:
        envelope = {**envelope, "task_id": task_id}
        self.store.save_run(task_id, version, envelope["status"], envelope)
        return {**envelope, "versions": self.store.versions(task_id)}

    @staticmethod
    def _envelope(status: str, conditions: ConditionSet | None, *, reasons: list[str] | None = None, **extra) -> dict:
        return {
            "status": status,
            "reasons": reasons or [],
            "condition_version": conditions.version if conditions else None,
            "conditions": conditions.model_dump(mode="json") if conditions else None,
            "clarifications": [c.model_dump(mode="json") for c in conditions.clarifications] if conditions else [],
            "kept": [], "excluded": [], "unverified": [],
            "stats": {}, "trace": {},
            **extra,
        }

    def _run(self, task_id: str, conditions: ConditionSet, *, changes: dict | None = None, previous: dict | None = None) -> dict:
        # Concurrent tasks with identical conditions share one computation; the result is
        # then bound to each task's own version below.
        key = ("run", conditions.fingerprint(), conditions.retrieval_text())
        try:
            body, _ = self._flight.do(key, lambda: self._compute(conditions))
        except Exception as e:
            return self._store(task_id, conditions.version, self._envelope("failed", conditions, reasons=[f"search failed: {e}"]))
        envelope = self._envelope(body["status"], conditions, reasons=body["reasons"],
                                  kept=body["kept"], excluded=body["excluded"], unverified=body["unverified"],
                                  stats=body["stats"], trace=body["trace"])
        if changes:
            envelope["changes"] = changes
        if previous and previous.get("status") in ("complete", "partial") and envelope["status"] in ("complete", "partial"):
            envelope["rank_changes"] = explain_rank_changes(previous, envelope)
        return self._store(task_id, conditions.version, envelope)

    def _compute(self, conditions: ConditionSet) -> dict:
        t0 = time.monotonic()
        if len(self.index) == 0:
            return {"status": "failed", "reasons": ["job index is empty"], "kept": [], "excluded": [],
                    "unverified": [], "stats": {}, "trace": {}}
        final = self._graph.invoke({
            "conditions": conditions, "budget": self.budget, "query": conditions.retrieval_text(),
            "retries": 0, "max_retries": self.max_retries, "llm_calls_used": 0, "started": t0, "timings": {},
        })
        retrieval, rerank_trace, verification = final["retrieval"], final["rerank_trace"], final["verification"]
        timings = final["timings"]

        reasons = list(verification.reasons)
        for name, info in retrieval.trace.get("channels", {}).items():
            if str(info.get("status", "")).startswith("failed"):  # "skipped" means not configured, not degraded
                reasons.append(f"retrieval channel unavailable: {name}")
        if str(rerank_trace.get("status", "")).startswith("failed"):
            reasons.append("reranker unavailable, kept retrieval order")
        failed = sum(1 for u in verification.unverified if u.note.startswith("judge failed"))
        if failed:
            reasons.append(f"{failed} judgement(s) failed after retries")

        return {
            "status": "partial" if reasons else "complete",
            "reasons": reasons,
            "kept": self._rank_kept([self._view(v, conditions=conditions) for v in verification.kept]),
            "excluded": [self._view(v) for v in verification.excluded],
            "unverified": [self._view(v, brief=True) for v in verification.unverified],
            "stats": {**verification.stats, "llm_calls_total": final.get("llm_calls_used", 0)},
            "trace": {
                "retrieval": retrieval.trace,
                "rerank": rerank_trace,
                "verification_plan": final.get("plan_trace", {}),
                "retries": final.get("retry_log", []),
                "timings_s": {**{k: round(v, 3) for k, v in timings.items()}, "total": round(time.monotonic() - t0, 3)},
            },
        }

    @staticmethod
    def _rank_kept(kept: list[dict]) -> list[dict]:
        """Soft preferences order the survivors (stable: pipeline order breaks ties)."""
        kept = sorted(kept, key=lambda j: (bool(j.get("to_confirm")), -(j["soft_score"] if j.get("soft_score") is not None else 0.0)))
        for i, j in enumerate(kept, 1):
            j["rank"] = i
        return kept

    def _view(self, v: VerifiedJob, *, brief: bool = False, conditions: ConditionSet | None = None) -> dict:
        snap = self.index.snapshot(v.candidate.job_key)
        out = {
            "job_key": snap.job_key, "title": snap.title, "company": snap.company, "location": snap.location,
            "url": snap.url, "content_hash": snap.content_hash,
            "rank": v.candidate.stage_ranks.get("final"), "stage_ranks": v.candidate.stage_ranks,
            "merged_keys": v.candidate.merged_keys, "note": v.note,
        }
        if brief or v.judgment is None:
            return out
        out["judgments"] = {cid: _judgment_view(j) for cid, j in v.judgment.judgments.items()}
        out["unconfirmed_hard"] = v.unconfirmed_hard
        if conditions is not None:
            out["soft_breakdown"] = soft_breakdown(conditions, v.judgment, snap)
            out["soft_score"] = soft_score(out["soft_breakdown"])
            out["to_confirm"] = to_confirm(conditions, v.judgment, snap)
            out["confirmation"] = "needs_confirmation" if out["to_confirm"] else "confirmed"
        if v.status == "excluded":
            out["evidence"] = [{"condition_id": j.condition_id, **_judgment_view(j)} for j in v.conflicts]
        return out
