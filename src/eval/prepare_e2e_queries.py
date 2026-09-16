"""
§7.6 端到端回答质量 — 对 20 条综合查询跑 run_pipeline，缓存四元组

从 40 条 test queries 中挑出 20 条覆盖多种字段组合的查询，
逐条跑 pipeline 缓存 (query, preferences, top-10 精简信息, answer)
到 data/eval_results/e2e_queries.json。

三家 LLM 后续基于这份缓存做端到端打分，无需重复调 pipeline。

用法:
    python -m src.eval.prepare_e2e_queries

成本:
    20 次 gpt-4o-mini 调用 × 2（parse_preferences + generate_answer）≈ $0.02
"""

import json
import os
import sys
import time
from pathlib import Path

from src.pipeline.graph import run_pipeline

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_QUERIES_PATH = ROOT / "data" / "test_queries.json"
# 允许通过环境变量重定向输出（例如跑 vNext 新 pipeline 对比时不覆盖已交付
# 报告引用的历史结果），默认行为不变。
E2E_RESULTS_DIR = Path(os.environ.get("E2E_EVAL_RESULTS_DIR") or (ROOT / "data" / "eval_results"))
OUT_PATH = E2E_RESULTS_DIR / "e2e_queries.json"

# 20 条覆盖字段组合的综合查询 id（从 40 条 test_queries 中挑选）：
# - 纯字段：q11（纯 remote）/ q08（纯 location）/ q21（纯 category）
# - 多字段：q01/q26/q28/q29（4-5 字段，高综合度）
# - 有 hard_filter：q32（phd 排除）
# - 纯描述（description only）：q34/q35
# - 覆盖全 7 类（backend/frontend/data/devops/fullstack/mobile/management）
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
    """只保留评分 / LLM 打分需要的关键字段，剔除原始 description 全文等冗余。"""
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
        print(f"[error] test_queries.json 缺失选中 id: {missing}", file=sys.stderr)
        return 1

    # 断点续跑
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
            print(f"[{i}/{len(SELECTED_IDS)}] {qid} 已缓存")
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
    print(f"\n已缓存 {len(results)} 条到 {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
