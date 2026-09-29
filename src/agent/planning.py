"""Decide which candidates the verification budget is spent on first.

Verification walks the ranked list until enough jobs survive, so its order decides where the
LLM calls go. Before any call, the program grades each candidate's scraper hints (salary,
location, work mode) against the HARD conditions. A candidate whose hints clearly contradict
one is very likely to be excluded, so it is moved behind the rest instead of consuming a call
that would probably end in exclusion. Nothing is excluded here: deferred candidates are still
verified if budget remains, and only a verified conflict ever removes a job.
"""

from __future__ import annotations

from typing import Callable

from src.agent.fit import fit_for
from src.agent.models import ConditionSet
from src.agent.retrieval import Candidate
from src.agent.snapshots import Snapshot

DEFER_AT_OR_BELOW = 0.15
DEFERRED_NOTE = "not checked: structured hints contradict a hard condition, checked last"


def plan_verification(
    candidates: list[Candidate], get_snapshot: Callable[[str], Snapshot], conditions: ConditionSet
) -> tuple[list[Candidate], dict]:
    hard = conditions.hard()
    first: list[Candidate] = []
    last: list[Candidate] = []
    deferred: list[dict] = []
    for cand in candidates:
        snap = get_snapshot(cand.job_key)
        bad = []
        for c in hard:
            fit = fit_for(c, snap)
            if fit is not None and fit.score <= DEFER_AT_OR_BELOW:
                bad.append({"condition_id": c.id, "fit": fit.score, "basis": fit.basis})
        if bad:
            last.append(cand)
            deferred.append({"job_key": cand.job_key, "conflicting_hints": bad})
        else:
            first.append(cand)
    return first + last, {"deferred": deferred, "deferred_count": len(deferred)}
