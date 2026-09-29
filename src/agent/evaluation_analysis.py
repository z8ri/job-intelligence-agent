"""Offline checks of the structured scoring and the rank-change explanation against a finished run.

  fit_vs_labels       does the hint-based fit agree with the annotator's per-condition status?
  explanation_check   do the per-condition reasons of a rank-change explanation add up to the real score change?
"""

from __future__ import annotations

from src.agent.evidence import JobJudgment
from src.agent.explain import MIN_CONTRIBUTION, explain_rank_changes
from src.agent.fit import fit_for
from src.agent.models import ConditionSet
from src.agent.planning import DEFER_AT_OR_BELOW
from src.agent.retrieval import JobIndex
from src.agent.scoring import soft_breakdown, soft_score

FIT_FIELDS = ("salary", "work_region", "remote_mode")
HIGH = 0.85


def fit_vs_labels(runs: dict, qrels: dict, index: JobIndex) -> dict:
    out: dict[str, dict] = {}
    for qid, run in runs.items():
        if "error" in run:
            continue
        cs = ConditionSet.model_validate(run["conditions"])
        for key, label in qrels.get(qid, {}).items():
            snap = index.snapshot(key)
            for c in cs.hard():
                if c.field not in FIT_FIELDS:
                    continue
                gold = label["hard"].get(c.id)
                row = out.setdefault(c.field, {"labelled": 0, "graded": 0, "gold": {}, "low": {}, "high": {}, "mid": {}})
                row["labelled"] += 1
                row["gold"][gold] = row["gold"].get(gold, 0) + 1
                fit = fit_for(c, snap)
                if fit is None:
                    continue
                row["graded"] += 1
                band = "low" if fit.score <= DEFER_AT_OR_BELOW else "high" if fit.score >= HIGH else "mid"
                row[band][gold] = row[band].get(gold, 0) + 1
    return out


def explanation_check(cs: ConditionSet, judgments: dict[str, JobJudgment], index: JobIndex, revision: dict[str, dict]) -> dict:
    """Apply `revision` ({condition id: field updates}) to one query's verified jobs and test the explanation.

    Jobs with a hard conflict are excluded (as the service does); the rest are ordered by soft score."""
    def build(conditions: ConditionSet, version: int) -> dict:
        kept, excluded = [], []
        for key, jj in judgments.items():
            evidence = [{"condition_id": c.id, "quote": jj.judgments[c.id].quote or ""} for c in conditions.hard()
                        if jj.verdict(c.id) == "conflict" and c.id in jj.judgments]
            if evidence:
                excluded.append({"job_key": key, "title": key, "evidence": evidence})
                continue
            bd = soft_breakdown(conditions, jj, index.snapshot(key))
            kept.append({"job_key": key, "title": key, "soft_breakdown": bd, "soft_score": soft_score(bd) or 0.0, "evidence": []})
        kept.sort(key=lambda j: -j["soft_score"])
        for i, j in enumerate(kept, 1):
            j["rank"] = i
        return {"kept": kept, "excluded": excluded, "unverified": [], "condition_version": version,
                "conditions": conditions.model_dump(mode="json")}

    before = build(cs, 1)
    data = cs.model_dump(mode="json")
    for c in data["conditions"]:
        c.update(revision.get(c["id"], {}))
    after = build(ConditionSet.model_validate(data), 2)
    exp = explain_rank_changes(before, after)
    old = {j["job_key"]: j for j in before["kept"]}
    new = {j["job_key"]: j for j in after["kept"]}
    moved = [j for j in exp["jobs"] if j["change"] in ("up", "down")]
    entered = [j for j in exp["jobs"] if j["change"] == "entered"]
    tolerance = MIN_CONTRIBUTION * max(1, len(after["conditions"]["conditions"]))
    exact = named = 0
    for j in moved:
        true_delta = new[j["job_key"]]["soft_score"] - old[j["job_key"]]["soft_score"]
        exact += abs(true_delta - sum(r["score_delta"] or 0.0 for r in j["reasons"])) <= tolerance + 1e-3
        named += any(r["condition_id"] in revision for r in j["reasons"])
    entered_named = sum(any(r["condition_id"] in revision for r in j["reasons"]) for j in entered)
    return {"jobs": len(judgments), "kept_before": len(before["kept"]), "kept_after": len(after["kept"]), "rank_moved": len(moved),
            "sum_matches_true_delta": exact, "moved_reason_names_revised_condition": named,
            "entered": len(entered), "entered_reason_names_revised_condition": entered_named}
