"""Offline analysis of a finished agent eval run (no network, no spend).

  python -m scripts.analyze_agent_eval --out data/eval_results_agent_run2/run3
"""

import argparse
import json
from pathlib import Path

from scripts.run_agent_eval import ROOT, build_index
from src.agent.evaluation import FrozenLLM
from src.agent.evaluation_analysis import explanation_check, fit_vs_labels
from src.agent.evidence import _openai_complete  # noqa: F401  (import check only)
from src.agent.models import ConditionSet
from src.agent.verification import Budget, JudgmentCache, Verifier


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, default=ROOT / "data" / "agent")
    args = p.parse_args()
    args.mode, args.embed = "replay", True
    runs = json.loads((args.out / "runs.json").read_text())
    qrels = json.loads((args.out / "qrels.json").read_text())
    index, _ = build_index(args, args.data_dir)

    fit = fit_vs_labels(runs, qrels, index)
    lines = ["# Structured scoring and explanation checks", "", "## Hint-based fit vs annotator labels (hard conditions)", "",
             "Gold = annotator status of the condition for that job. low = fit <= 0.15 (would be deferred), high = fit >= 0.85.", "",
             "| condition | labelled | graded | gold satisfied/violated/unstated overall | low: sat/viol/unst | high: sat/viol/unst |", "|---|---|---|---|---|---|"]
    tri = lambda d: "/".join(str(d.get(s, 0)) for s in ("satisfied", "violated", "unstated"))
    for field, r in fit.items():
        lines.append(f"| {field} | {r['labelled']} | {r['graded']} | {tri(r['gold'])} | {tri(r['low'])} | {tri(r['high'])} |")

    llm = FrozenLLM(args.out.parent / "llm_log.db", mode="replay")
    lines += ["", "## Rank-change explanation after the user relaxes one hard condition to a soft preference (weight 0.5)", "",
              "| query | relaxed | verified | kept before -> after | rank moved | moved: reasons sum to true score change | moved: reason names the relaxed condition | entered | entered: reason names it |",
              "|---|---|---|---|---|---|---|---|---|"]
    totals = [0] * 6
    for qid, run in runs.items():
        cs = ConditionSet.model_validate(run["conditions"])
        target = next((c for c in cs.hard() if c.field in ("work_region", "remote_mode", "salary", "seniority", "employment_type")), None)
        if target is None:
            continue
        verifier = Verifier(JudgmentCache(), complete=llm.view("judge", None), model=llm.model)
        cands = index.search(cs.retrieval_text(), top_n=20).candidates
        res = verifier.verify(cands, index.snapshot, cs, Budget(target_kept=20, max_candidates=20, max_llm_calls=20, deadline_s=3600.0, max_workers=4, max_consecutive_failures=5))
        judgments = {v.candidate.job_key: v.judgment for v in [*res.kept, *res.excluded] if v.judgment}
        r = explanation_check(cs, judgments, index, {target.id: {"strength": "soft", "weight": 0.5}})
        for i, key in enumerate(("rank_moved", "sum_matches_true_delta", "moved_reason_names_revised_condition", "entered", "entered_reason_names_revised_condition")):
            totals[i] += r[key]
        lines.append(f"| {qid} | {target.field} | {r['jobs']} | {r['kept_before']} -> {r['kept_after']} | {r['rank_moved']} | {r['sum_matches_true_delta']}/{r['rank_moved']} | "
                     f"{r['moved_reason_names_revised_condition']}/{r['rank_moved']} | {r['entered']} | {r['entered_reason_names_revised_condition']}/{r['entered']} |")
    lines.append(f"| total | | | | {totals[0]} | {totals[1]}/{totals[0]} | {totals[2]}/{totals[0]} | {totals[3]} | {totals[4]}/{totals[3]} |")
    (args.out / "analysis.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
