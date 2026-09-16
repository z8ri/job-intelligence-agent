"""
Section 7.6 end-to-end answer quality: run run_pipeline on 20 composite queries
and cache the resulting tuples.

Picks 20 of the 40 test queries that cover a variety of field combinations,
runs the pipeline on each and caches (query, preferences, slimmed top-10, answer)
to data/eval_results/e2e_queries.json.

The three LLM raters then score end-to-end from this cache, so the pipeline
never has to be re-run.

Usage:
    python -m src.eval.prepare_e2e_queries

Cost:
    20 x 2 gpt-4o-mini calls (parse_preferences + generate_answer), roughly $0.02
"""

import json
import os
import sys
import time
from pathlib import Path

from src.pipeline.graph import run_pipeline

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_QUERIES_PATH = ROOT / "data" / "test_queries.json"
# Output can be redirected via an environment variable (e.g. when running the
# vNext pipeline for comparison, so historical results cited by the delivered
# report are not overwritten). Default behavior is unchanged.
E2E_RESULTS_DIR = Path(os.environ.get("E2E_EVAL_RESULTS_DIR") or (ROOT / "data" / "eval_results"))
OUT_PATH = E2E_RESULTS_DIR / "e2e_queries.json"

# 20 composite query ids covering different field combinations (selected from the 40 test_queries):
# - single field: q11 (remote only) / q08 (location only) / q21 (category only)
# - multi-field: q01/q26/q28/q29 (4-5 fields, highly composite)
# - with hard_filter: q32 (excludes PhD)
# - description only: q34/q35
# - covers all 7 categories (backend/frontend/data/devops/fullstack/mobile/management)
SELECTED_IDS = [
    "q01",  # Remote Python backend 150k+ (salary+remote+tags+category)
    "q05",  # Data science 130-160k (salary+desc+category)
    "q07",  # Boston backend (location+category)
    "q11",  # Fully remote senior (remote+desc)
    "q14",  # 100% remote data engineering (remote+desc+category)
    "q15",  # React+TypeScript frontend (tags+category)
    "q16",  # Kubernetes+Terraform DevOps (tags+category)
    "q20",  # Flutter/React Native mobile (tags+category)
    "q22",  # Engineering manager (desc+category)
    "q25",  # SRE (desc+category)
    "q26",  # Remote ML NY 130k+ (5-field)
    "q27",  # Backend Go hybrid 160k (salary+remote+tags+category)
    "q28",  # Full stack JS SF remote 140k (5-field)
    "q29",  # Senior data engineer Spark/Kafka 170k (5-field)
    "q30",  # React frontend Chicago 120k (4-field)
    "q31",  # DevOps AWS/Docker Austin hybrid (4-field)
    "q32",  # Python/Java backend 150k no PhD (hard_filter)
    "q33",  # Management Denver 180k (salary+location+category)
    "q34",  # Good culture for juniors (pure desc)
    "q35",  # Startup equity (pure desc)
]


def _slim_job(job: dict) -> dict:
    """Keep only the fields needed for scoring / LLM rating; drop the full description and other bulk."""
    return {
        "job_id": job.get("job_id"),
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "remote": job.get("remote"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "tags": job.get("tags") or [],
        "category": job.get("category"),
        "predicted_category": job.get("predicted_category"),
        "description": (job.get("description") or "")[:400],
        "final_score": job.get("final_score"),
        "score_breakdown": job.get("score_breakdown") or {},
    }


def main() -> int:
    if not TEST_QUERIES_PATH.exists():
        print(f"[error] {TEST_QUERIES_PATH} not found", file=sys.stderr)
        return 1

    with TEST_QUERIES_PATH.open("r", encoding="utf-8") as f:
        all_queries = {q["id"]: q for q in json.load(f)}

    missing = [qid for qid in SELECTED_IDS if qid not in all_queries]
    if missing:
        print(f"[error] test_queries.json is missing selected ids: {missing}", file=sys.stderr)
        return 1

    # Resumable
    existing: dict = {}
    if OUT_PATH.exists():
        with OUT_PATH.open("r", encoding="utf-8") as f:
            for e in json.load(f):
                existing[e["query_id"]] = e

    results = []
    for i, qid in enumerate(SELECTED_IDS, start=1):
        q = all_queries[qid]
        if qid in existing and "answer" in existing[qid]:
            results.append(existing[qid])
            print(f"[{i}/{len(SELECTED_IDS)}] {qid} cached")
            continue
        try:
            start = time.time()
            state = run_pipeline(q["query"], top_k=10)
            elapsed = time.time() - start
            ranked = state.get("classified_jobs") or state.get("ranked_jobs") or []
            record = {
                "query_id": qid,
                "query": q["query"],
                "preferences": state.get("preferences") or {},
                "top_jobs": [_slim_job(j) for j in ranked[:10]],
                "answer": state.get("answer") or "",
            }
            results.append(record)
            print(f"[{i}/{len(SELECTED_IDS)}] {qid} ok ({elapsed:.1f}s, {len(ranked)} jobs)")
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[{i}/{len(SELECTED_IDS)}] {qid} FAILED: {e}", file=sys.stderr)
            results.append({"query_id": qid, "query": q["query"], "error": str(e)})

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nCached {len(results)} entries to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
