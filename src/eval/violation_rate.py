"""硬约束违反率：老系统历史 Top-K 结果里，有多少比例其实是兼职/合同工/实习
这类本该被 Verifier 拦下的职位——量化"没有 Verifier 之前，结果有多脏"。

纯本地计算，不调 LLM：直接读老系统的历史排名 + 历史 preferences + 原始 query
文本，对每条候选跑 src/scoring/verifier.py::verify_jobs()（规则式判断）。

不覆盖任何历史文件——只读 data/eval_results/、data/test_queries.json，
产物写到 data/eval_results_vnext/violation_rate.json。

用法:
    python -m src.eval.violation_rate
"""

import json

from src.eval import PROJECT_ROOT
from src.db.database import get_connection
from src.scoring.verifier import verify_jobs

OLD_RANKINGS_PATH = PROJECT_ROOT / "data" / "eval_results" / "rankings.json"
OLD_PREFS_CACHE_PATH = PROJECT_ROOT / "data" / "eval_results" / "preferences_cache.json"
TEST_QUERIES_PATH = PROJECT_ROOT / "data" / "test_queries.json"
NEW_RANKINGS_PATH = PROJECT_ROOT / "data" / "eval_results_vnext" / "rankings.json"
OUT_PATH = PROJECT_ROOT / "data" / "eval_results_vnext" / "violation_rate.json"

TOP_N = 5


def _load_query_texts() -> dict[str, str]:
    with open(TEST_QUERIES_PATH, encoding="utf-8") as f:
        queries = json.load(f)
    return {q["id"]: q["query"] for q in queries}


def _fetch_jobs(job_ids: set[str]) -> dict[str, dict]:
    if not job_ids:
        return {}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(job_ids))
            cur.execute(f"SELECT * FROM jobs WHERE job_id IN ({placeholders})", list(job_ids))
            rows = cur.fetchall()
        return {r["job_id"]: r for r in rows}
    finally:
        conn.close()


def compute_violation_rate(
    rankings: dict[str, list[str]],
    prefs_cache: dict[str, dict],
    query_texts: dict[str, str],
    top_n: int = TOP_N,
) -> dict:
    """rankings: {qid: [job_id, ...]}（已经是某一个 config 的排名）。
    返回 {"total": int, "rejected": int, "rate": float, "examples": [...]}。
    """
    needed_ids: set[str] = set()
    for qid, jids in rankings.items():
        needed_ids.update(jids[:top_n])
    jobs_by_id = _fetch_jobs(needed_ids)

    total = 0
    rejected = 0
    examples = []

    for qid, jids in rankings.items():
        if qid not in prefs_cache:
            continue
        preferences = prefs_cache[qid]["preferences"]
        query_text = query_texts.get(qid, "")
        top_jobs = [dict(jobs_by_id[jid]) for jid in jids[:top_n] if jid in jobs_by_id]

        verified = verify_jobs(top_jobs, preferences, query_text)
        for job in verified:
            total += 1
            if job["verification_status"] == "rejected":
                rejected += 1
                examples.append({
                    "qid": qid,
                    "query": query_text,
                    "job_id": job["job_id"],
                    "title": job.get("title"),
                    "reason": job["verification_reason"],
                })

    rate = rejected / total if total else 0.0
    return {"total": total, "rejected": rejected, "rate": rate, "examples": examples}


def main() -> None:
    with open(OLD_PREFS_CACHE_PATH, encoding="utf-8") as f:
        prefs_cache = json.load(f)
    query_texts = _load_query_texts()

    with open(OLD_RANKINGS_PATH, encoding="utf-8") as f:
        old_rankings = json.load(f)
    old_config = "all_adaptive_weights"
    print(f"[old baseline] config={old_config}")
    old_result = compute_violation_rate(old_rankings[old_config], prefs_cache, query_texts)
    print(f"  {old_result['rejected']}/{old_result['total']} = {old_result['rate']:.1%} 会被判 rejected")

    result = {"old": {"config": old_config, **old_result}}

    if NEW_RANKINGS_PATH.exists():
        with open(NEW_RANKINGS_PATH, encoding="utf-8") as f:
            new_rankings = json.load(f)
        new_config = "hybrid_rrf_reranked"
        if new_config in new_rankings:
            print(f"\n[新检索方式候选池本身] config={new_config}")
            new_result = compute_violation_rate(new_rankings[new_config], prefs_cache, query_texts)
            print(f"  {new_result['rejected']}/{new_result['total']} = {new_result['rate']:.1%} 会被判 rejected")
            result["new_retrieval_pool"] = {"config": new_config, **new_result}

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n已写入 {OUT_PATH}")


if __name__ == "__main__":
    main()
