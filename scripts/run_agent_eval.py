"""Agent evaluation driver.

  python -m scripts.run_agent_eval run --mode replay            # offline, from the frozen log
  python -m scripts.run_agent_eval run --mode record --embed    # manual opt-in: may spend, capped by --max-usd
  python -m scripts.run_agent_eval report
  python -m scripts.run_agent_eval export-review --split holdout
  python -m scripts.run_agent_eval import-review --file reviewed.csv

Nothing here runs in the test suite. `record` needs OPENAI_API_KEY (see src/llm).
"""

import argparse
import json
import sys
from pathlib import Path

from src.agent.embeddings import CachedEmbedder, EmbeddingCache, EmbeddingError, default_model_name, openai_embed_fn
from src.agent.evaluation import (
    FrozenLLM, build_manifest, check_split_isolation, compute_metrics, export_review, import_review, load_queries,
    render_report, run_eval,
)
from src.agent.retrieval import JobIndex
from src.agent.snapshots import SnapshotStore, import_legacy_json

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "eval_results_agent" / "run1"


def _refuse_embedding(texts):
    raise EmbeddingError("replay mode: embedding not cached and live calls are disabled")


def build_index(args, data: Path):
    data.mkdir(parents=True, exist_ok=True)
    snapshots = SnapshotStore(data / "snapshots.db")
    if snapshots.count() == 0:
        n = import_legacy_json(ROOT / "data" / "structured_jobs.json", snapshots, fetched_at="2026-03-01T00:00:00+00:00")
        print(f"imported {n} legacy jobs into {data / 'snapshots.db'}")
    model = default_model_name()
    embedder = None
    if args.embed or (data / "embeddings.db").exists():
        live = args.mode == "record" and args.embed
        embedder = CachedEmbedder(openai_embed_fn() if live else _refuse_embedding, model, EmbeddingCache(data / "embeddings.db"))
    return JobIndex(snapshots.all_latest(), embedder), model if embedder else None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["run", "report", "export-review", "import-review"])
    p.add_argument("--mode", choices=["replay", "record"], default="replay")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--queries", type=Path, default=ROOT / "data" / "agent_eval" / "queries.json")
    p.add_argument("--data-dir", type=Path, default=ROOT / "data" / "agent")
    p.add_argument("--max-usd", type=float, default=0.20, help="cumulative cap on live LLM spend recorded in the log")
    p.add_argument("--embed", action="store_true", help="use the embedding channels (record mode embeds uncached jobs live)")
    p.add_argument("--reranker", action="store_true", help="include the cross-encoder rerank system")
    p.add_argument("--split", choices=["dev", "holdout"])
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--max-candidates", type=int, default=20)
    p.add_argument("--file", type=Path)
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    runs_path, qrels_path = args.out / "runs.json", args.out / "qrels.json"

    if args.command == "report":
        runs, qrels = json.loads(runs_path.read_text()), json.loads(qrels_path.read_text())
        manifest = json.loads((args.out / "manifest.json").read_text()) if (args.out / "manifest.json").exists() else None
        metrics = compute_metrics(runs, qrels, k=args.k)
        (args.out / "metrics.json").write_text(json.dumps(metrics, indent=1, ensure_ascii=False))
        (args.out / "report.md").write_text(render_report(metrics, manifest))
        print(render_report(metrics, manifest))
        return 0

    queries = load_queries(args.queries)
    problems = check_split_isolation(queries)
    if problems:
        print("query set problems:\n  " + "\n  ".join(problems))
        return 1
    if args.split:
        queries = [q for q in queries if q.split == args.split]

    index, embed_model = build_index(args, args.data_dir)
    if args.command == "export-review":
        n = export_review(json.loads(runs_path.read_text()), index, args.out / f"review_{args.split or 'all'}.csv", split=args.split)
        print(f"wrote {n} rows")
        return 0
    if args.command == "import-review":
        runs, qrels = json.loads(runs_path.read_text()), json.loads(qrels_path.read_text())
        merged, problems = import_review(args.file, qrels, runs)
        qrels_path.write_text(json.dumps(qrels, ensure_ascii=False, indent=1, sort_keys=True))
        print(f"merged {merged} human labels; {len(problems)} problems")
        [print("  " + x) for x in problems]
        return 0

    scorer = None
    if args.reranker:
        from src.agent.rerank import CrossEncoderScorer

        scorer = CrossEncoderScorer()
    lives = {}
    if args.mode == "record":
        from src.agent import conditions, evidence

        def annotate_live(system, user):
            return evidence._openai_complete(system, user, run_id="agent_eval_annotate")

        lives = dict(parse_live=conditions._openai_complete, judge_live=evidence._openai_complete, annotate_live=annotate_live)
    llm = FrozenLLM(args.out.parent / "llm_log.db", mode=args.mode, max_usd=args.max_usd)
    result = run_eval(queries, index, scorer, llm, args.out, k=args.k, max_candidates=args.max_candidates, log=print, **lives)
    manifest = build_manifest(index, queries, k=args.k, max_candidates=args.max_candidates, scorer=scorer, embed_model=embed_model)
    manifest["live_llm_spend_usd_estimated"] = round(llm.live_spent_usd(), 4)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"live spend so far (estimated): ${llm.live_spent_usd():.4f} of ${args.max_usd:.2f}")
    return 2 if result["stopped"] else 0


if __name__ == "__main__":
    sys.exit(main())
