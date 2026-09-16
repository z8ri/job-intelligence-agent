"""
§7.2 偏好提取准确率 — 缓存我们系统（gpt-4o-mini）的偏好提取输出

对 data/test_queries.json 的 40 条查询依次调 parse_preferences，
结果缓存到 data/eval_results/pref_system_output.json。

用法:
    python -m src.eval.cache_pref_system_output

成本:
    40 次 gpt-4o-mini 调用，约 $0.005
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

    # 断点续跑：若已有缓存则合并（方便中断后继续）
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
            print(f"[{i+1}/{len(queries)}] {qid} 已缓存")
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
            # 增量落盘，防中断
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[{i+1}/{len(queries)}] {qid} FAILED: {e}", file=sys.stderr)
            results.append({"query_id": qid, "query": q["query"], "error": str(e)})

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已缓存 {len(results)} 条到 {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
