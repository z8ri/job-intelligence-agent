"""Soft-preference scoring and the confirmation list, computed by the program.

Hard conditions decide who is shown (only verified conflicts exclude). Soft conditions
do not filter: each contributes its weight times a score, and the weighted mean orders the
kept jobs, with the pipeline order breaking ties.

A condition's score follows one rule, evidence first and structure second:
  * evidence says support  -> 1.0
  * evidence says conflict -> 0.0, or at most 0.25 when the structured fit shows a near miss
  * evidence says unknown  -> the structured fit (salary / location / work mode) if the
                              snapshot has one, else 0.5 (neither rewarded nor punished)
The model only supplies verdicts; how they are combined and weighted is fixed here.
"""

from __future__ import annotations

from src.agent.evidence import JobJudgment
from src.agent.fit import fit_for
from src.agent.models import Condition, ConditionSet
from src.agent.snapshots import Snapshot

VERDICT_SCORE = {"support": 1.0, "unknown": 0.5, "conflict": 0.0}
NEAR_MISS_CAP = 0.25


def condition_score(condition: Condition, verdict: str, snapshot: Snapshot | None) -> dict:
    fit = fit_for(condition, snapshot)
    if verdict == "support" or fit is None:
        score, source = VERDICT_SCORE[verdict], "evidence"
    elif verdict == "conflict":
        score, source = min(fit.score, NEAR_MISS_CAP), "evidence+structured"
    else:
        score, source = fit.score, "structured"
    out = {"score": round(score, 4), "source": source}
    if fit is not None:
        out["fit"] = fit.score
        out["fit_basis"] = fit.basis
    return out


def soft_breakdown(conditions: ConditionSet, judgment: JobJudgment | None, snapshot: Snapshot | None = None) -> list[dict]:
    if judgment is None:
        return []
    rows = []
    for c in conditions.soft():
        verdict = judgment.verdict(c.id)
        rows.append({"condition_id": c.id, "field": c.field, "weight": c.effective_weight, "verdict": verdict,
                     **condition_score(c, verdict, snapshot)})
    return rows


def soft_score(breakdown: list[dict]) -> float | None:
    """Weighted mean in [0, 1]; None when the request has no soft conditions."""
    total = sum(b["weight"] for b in breakdown)
    if not breakdown or total <= 0:
        return None
    return round(sum(b["weight"] * b["score"] for b in breakdown) / total, 4)


def to_confirm(conditions: ConditionSet, judgment: JobJudgment | None, snapshot: Snapshot | None) -> list[dict]:
    """Hard conditions the posting neither confirms nor contradicts. Such a job stays in the
    list but is never treated as having met them; the entry says what is missing and what
    could settle it."""
    if judgment is None:
        return []
    step = "check the posting link" if snapshot is not None and snapshot.url else "no source link stored for this posting; confirm with the employer"
    out = []
    for c in conditions.hard():
        if judgment.verdict(c.id) == "unknown":
            j = judgment.judgments.get(c.id)
            out.append({"condition_id": c.id, "field": c.field, "asked": c.quote,
                        "why": (j.reason if j and j.reason else "the posting does not say"), "next_step": step})
    return out
