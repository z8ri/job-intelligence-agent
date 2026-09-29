"""Live measurement: condition revision on a warm service vs a cold full recompute.

For each new request and each kind of revision it records LLM judge calls, wall-clock time and
whether the two ways give the same result. Uses the real LLM, embeddings and reranker (spends money,
guarded by --max-usd).

  python -m scripts.eval_incremental
"""

import argparse
import json
import shutil
import statistics
import tempfile
import time
from pathlib import Path

from scripts.run_agent_eval import ROOT
from src.agent.embeddings import CachedEmbedder, EmbeddingCache, default_model_name, openai_embed_fn
from src.agent.evaluation import COMPLETION_ESTIMATE, _cost, est_tokens
from src.agent.evidence import _openai_complete
from src.agent.conditions import parse_conditions
from src.agent.models import ConditionSet
from src.agent.rerank import CrossEncoderScorer
from src.agent.retrieval import JobIndex
from src.agent.service import SearchService
from src.agent.snapshots import SnapshotStore
from src.agent.tasks import TaskStore
from src.agent.verification import Budget, JudgmentCache, Verifier
from src.llm import MODEL

RELAXABLE = ("work_region", "salary", "seniority", "skill", "remote_mode")


class Meter:
    def __init__(self, max_usd: float):
        self.max_usd, self.usd, self.calls, self.latencies = max_usd, 0.0, 0, []

    def __call__(self, system: str, user: str) -> str:
        cost = _cost(MODEL, est_tokens(system) + est_tokens(user), COMPLETION_ESTIMATE)
        if self.usd + cost > self.max_usd:
            raise RuntimeError("spend guard reached")
        t = time.monotonic()
        out = _openai_complete(system, user, run_id="incremental_eval")
        self.latencies.append(time.monotonic() - t)
        self.usd += cost
        self.calls += 1
        return out


class Section:
    """Counts the calls of a shared meter inside one measured section."""

    def __init__(self, meter: Meter):
        self.meter = meter

    def __enter__(self):
        self.c0, self.t0 = self.meter.calls, time.monotonic()
        return self

    def __exit__(self, *exc):
        self.calls, self.seconds = self.meter.calls - self.c0, time.monotonic() - self.t0


def revisions(cs: ConditionSet) -> dict[str, dict]:
    hard = [c for c in cs.hard() if c.field != "role_focus"]
    soft = cs.soft()
    out: dict[str, dict] = {}
    if soft:
        out["weight_change"] = {"weights": {soft[0].id: 1.0 if soft[0].effective_weight < 0.9 else 0.2}}
        out["tighten_soft_to_hard"] = {"strengths": {soft[0].id: "hard"}}
    relax = next((c for c in hard if c.field in RELAXABLE), None)
    if relax:
        out["relax_hard_to_soft"] = {"strengths": {relax.id: "soft"}}
    if hard:
        out["remove_condition"] = {"remove": [hard[-1].id]}
    return out


def view(body: dict) -> dict:
    return {"kept": [j["job_key"] for j in body["kept"]], "excluded": sorted(j["job_key"] for j in body["excluded"]),
            "soft": {j["job_key"]: j.get("soft_score") for j in body["kept"]}}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, default=ROOT / "data" / "agent_eval" / "incremental_queries.json")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "eval_results_agent_run2" / "incremental")
    p.add_argument("--max-usd", type=float, default=0.17)
    p.add_argument("--only", type=int, nargs="*", help="query indexes to run (default all)")
    p.add_argument("--noise-only", action="store_true", help="only re-run each query's initial conditions cold, to measure run-to-run LLM noise")
    p.add_argument("--tag", default="results", help="output file stem")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp())
    shutil.copy(ROOT / "data" / "agent" / "embeddings.db", work / "embeddings.db")
    embedder = CachedEmbedder(openai_embed_fn(), default_model_name(), EmbeddingCache(work / "embeddings.db"))
    index = JobIndex(SnapshotStore(ROOT / "data" / "agent" / "snapshots.db").all_latest(), embedder)
    scorer = CrossEncoderScorer()
    budget = Budget(target_kept=5, max_candidates=20, max_llm_calls=30, deadline_s=120.0, max_workers=4, max_consecutive_failures=3)
    meter = Meter(args.max_usd)

    def service(fixed: ConditionSet | None) -> SearchService:
        svc = SearchService(index, scorer, Verifier(JudgmentCache(), complete=meter, model=MODEL), TaskStore(work / f"t{time.time_ns()}.db"),
                            parse=(lambda q: fixed) if fixed else parse_conditions, budget=budget, retrieve_top_n=50, rerank_depth=20)
        return svc

    index.search("warm up retrieval", top_n=5)
    scorer.score([("warm up", "a job posting")])

    rows = []
    try:
        for qi, query in enumerate(json.loads(args.queries.read_text())):
            if args.only is not None and qi not in args.only:
                continue
            cs = parse_conditions(query)
            warm = service(cs)
            if args.noise_only:
                with Section(meter) as one:
                    a = view(warm._compute(cs))
                with Section(meter) as two:
                    b = view(service(None)._compute(cs))
                rows.append({"query": query, "revision": "noise_floor", "run_a_calls": one.calls, "run_b_calls": two.calls,
                             "same_ordered_kept": a["kept"] == b["kept"], "same_kept_set": set(a["kept"]) == set(b["kept"]),
                             "same_excluded": a["excluded"] == b["excluded"], "kept_a": a["kept"], "kept_b": b["kept"],
                             "excluded_a": len(a["excluded"]), "excluded_b": len(b["excluded"])})
                print(f"{query[:60]}: noise floor order={rows[-1]['same_ordered_kept']} set={rows[-1]['same_kept_set']} excl={rows[-1]['same_excluded']}")
                continue
            with Section(meter) as initial:
                v1 = warm.start(query)
            print(f"{query[:60]}: initial {initial.calls} calls {initial.seconds:.1f}s status={v1['status']}")
            for kind, rev in revisions(cs).items():
                # a fresh task with the same v1 conditions on the warm cache, then the revision
                task = warm.start(query)
                with Section(meter) as inc:
                    r = warm.revise(task["task_id"], task["condition_version"], **rev)
                cold = service(None)
                revised = ConditionSet.model_validate(r["conditions"])
                with Section(meter) as full:
                    body = cold._compute(revised)
                a, b = view(r), view(body)
                same_list = a["kept"] == b["kept"]
                same_set = set(a["kept"]) == set(b["kept"])
                rows.append({"query": query, "revision": kind, "status": r["status"],
                             "incremental": {"llm_calls": inc.calls, "seconds": round(inc.seconds, 2), "stages": r["trace"]["timings_s"]},
                             "full_recompute": {"llm_calls": full.calls, "seconds": round(full.seconds, 2), "stages": body["trace"]["timings_s"]},
                             "same_ordered_kept": same_list, "same_kept_set": same_set, "same_excluded": a["excluded"] == b["excluded"],
                             "kept_incremental": a["kept"], "kept_full": b["kept"]})
                print(f"  {kind}: incremental {inc.calls} calls {inc.seconds:.1f}s | full {full.calls} calls {full.seconds:.1f}s | same order={same_list} set={same_set}")
    except RuntimeError as e:
        print("stopped:", e)
    (args.out / f"{args.tag}.json").write_text(json.dumps({"spend_usd_estimated": round(meter.usd, 4), "rows": rows}, indent=1, ensure_ascii=False))
    print(f"estimated spend ${meter.usd:.4f}; judge calls {meter.calls}; median live call latency {statistics.median(meter.latencies):.2f}s")


if __name__ == "__main__":
    main()
