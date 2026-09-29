"""List every job a verifying system shows that the silver labels call wrong, next to the judgments
the verifier made for it (verdict + quote). Replays the frozen LLM log: no network, no spend.

  python -m scripts.diagnose_wrong_accepts --run data/eval_results_agent_run2/run3 --system verify_ondemand
"""

import argparse
import json
import sys
from pathlib import Path

from src.agent.evaluation import FrozenLLM, is_valid
from src.agent.models import ConditionSet
from src.agent.retrieval import Candidate, JobIndex
from src.agent.snapshots import SnapshotStore
from src.agent.verification import Budget, JudgmentCache, Verifier

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, default=ROOT / "data" / "eval_results_agent_run2" / "run3")
    p.add_argument("--system", default="verify_ondemand")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--out", type=Path)
    a = p.parse_args()

    runs = json.loads((a.run / "runs.json").read_text())
    qrels = json.loads((a.run / "qrels.json").read_text())
    snaps = SnapshotStore(ROOT / "data" / "agent" / "snapshots.db")
    index = JobIndex(snaps.all_latest(), None)
    llm = FrozenLLM(a.run.parent / "llm_log.db", mode="replay")
    rows = []
    for qid, run in sorted(runs.items()):
        if "error" in run:
            continue
        cs = ConditionSet.model_validate(run["conditions"])
        hard_ids = [c.id for c in cs.hard()]
        sysrun = run["systems"][a.system]
        labels = qrels.get(qid, {})
        keys = sysrun["shown"][: a.k] + sysrun.get("excluded", [])
        view = llm.view(a.system)
        res = Verifier(JudgmentCache(), complete=view, model=llm.model).verify(
            [Candidate(k, 0.0) for k in keys], index.snapshot, cs,
            Budget(target_kept=len(keys), max_candidates=len(keys), max_llm_calls=len(keys), deadline_s=3600.0, max_workers=1),
        )
        verified = {v.candidate.job_key: v for v in [*res.kept, *res.excluded]}
        conds = {c.id: c for c in cs.conditions}
        for key in keys:
            lab, v = labels.get(key), verified.get(key)
            if lab is None or v is None or v.judgment is None:
                continue
            shown = key in sysrun["shown"][: a.k]
            silver_bad = lab["relevance"] == 0 or any(lab["hard"].get(i) == "violated" for i in hard_ids)
            silver_valid = is_valid(lab, hard_ids)
            if shown and silver_bad:
                kind = "wrong_accept"
            elif not shown and silver_valid:
                kind = "wrong_exclude"
            else:
                continue
            snap = index.snapshot(key)
            rows.append({
                "kind": kind, "query": qid, "request": run["query"], "job": key, "title": snap.title,
                "company": snap.company, "location": snap.location, "silver_relevance": lab["relevance"],
                "silver_reason": lab["reason"],
                "hard": [
                    {"id": i, "field": conds[i].field, "quote": conds[i].quote, "silver": lab["hard"].get(i),
                     "verdict": v.judgment.verdict(i),
                     "evidence": (v.judgment.judgments[i].quote if i in v.judgment.judgments else None),
                     "reason": (v.judgment.judgments[i].reason if i in v.judgment.judgments else None)}
                    for i in hard_ids
                ],
            })
    text = json.dumps(rows, ensure_ascii=False, indent=1)
    if a.out:
        a.out.write_text(text)
    print(f"{sum(r['kind']=='wrong_accept' for r in rows)} wrong accepts, {sum(r['kind']=='wrong_exclude' for r in rows)} wrong excludes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
