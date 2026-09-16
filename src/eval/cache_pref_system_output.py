"""
Section 7.2 preference-extraction accuracy: cache our system's (gpt-4o-mini)
preference-extraction output.

Runs parse_preferences on each of the 40 queries in data/test_queries.json
and caches the results to data/eval_results/pref_system_output.json.

Usage:
    python -m src.eval.cache_pref_system_output

Cost:
    40 gpt-4o-mini calls, roughly $0.005
"""

import json
import sys
import time
from pathlib import Path

from src.llm.query_understanding import parse_preferences

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_QUERIES_PATH = ROOT / "data" / "test_queries.json"
OUT_PATH = ROOT / "data" / "eval_results" / "pref_system_output.json"


def main() -> int:
    if not TEST_QUERIES_PATH.exists():
        print(f"[error] {TEST_QUERIES_PATH} not found", file=sys.stderr)
        return 1

    with TEST_QUERIES_PATH.open("r", encoding="utf-8") as f:
        queries = json.load(f)

    # Resumable: merge with any existing cache so an interrupted run can continue
    existing: dict = {}
    if OUT_PATH.exists():
        with OUT_PATH.open("r", encoding="utf-8") as f:
            for e in json.load(f):
                existing[e["query_id"]] = e

    results = []
    for i, q in enumerate(queries):
        qid = q["id"]
        if qid in existing:
            results.append(existing[qid])
            print(f"[{i+1}/{len(queries)}] {qid} cached")
            continue
        try:
            start = time.time()
            out = parse_preferences(q["query"])
            elapsed = time.time() - start
            print(f"[{i+1}/{len(queries)}] {qid} ok ({elapsed:.1f}s)")
            results.append({
                "query_id": qid,
                "query": q["query"],
                "preferences": out["preferences"],
                "weights": out["weights"],
            })
            # Write incrementally so nothing is lost on interruption
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[{i+1}/{len(queries)}] {qid} FAILED: {e}", file=sys.stderr)
            results.append({"query_id": qid, "query": q["query"], "error": str(e)})

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nCached {len(results)} entries to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
