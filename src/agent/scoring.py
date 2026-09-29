"""Soft-preference scoring over verified judgements.

Hard conditions decide who is shown (only verified conflicts exclude). Soft conditions
do not filter: each contributes its weight times a verdict score, and the weighted mean
orders the kept jobs, with the pipeline order breaking ties. Unknown is neutral (0.5)
so a job is neither rewarded nor punished for what the text does not say.
"""

from __future__ import annotations

from src.agent.models import ConditionSet
from src.agent.evidence import JobJudgment

VERDICT_SCORE = {"support": 1.0, "unknown": 0.5, "conflict": 0.0}


def soft_breakdown(conditions: ConditionSet, judgment: JobJudgment | None) -> list[dict]:
    if judgment is None:
        return []
    return [
        {"condition_id": c.id, "field": c.field, "weight": c.effective_weight, "verdict": judgment.verdict(c.id),
         "score": VERDICT_SCORE[judgment.verdict(c.id)]}
        for c in conditions.soft()
    ]


def soft_score(breakdown: list[dict]) -> float | None:
    """Weighted mean in [0, 1]; None when the request has no soft conditions."""
    total = sum(b["weight"] for b in breakdown)
    if not breakdown or total <= 0:
        return None
    return round(sum(b["weight"] * b["score"] for b in breakdown) / total, 4)
