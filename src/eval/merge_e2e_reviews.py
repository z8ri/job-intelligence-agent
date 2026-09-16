"""
§7.6 端到端回答质量 — 合并三家 LLM 独立打分，校验格式

读取 data/reviews_e2e/{claude,chatgpt,gemini}.json
（格式：[{query_id, relevance:{comment,score}, completeness:{...}, readability:{...}}]）

输出 data/eval_results/e2e_gold.json：
    [{
        "query_id": "q01",
        "per_rater": {"claude": {r, c, d}, "chatgpt": {...}, "gemini": {...}},
        "mean": {"relevance": 4.33, "completeness": 4.00, "readability": 4.67},
        "std":  {"relevance": 0.58, "completeness": 0.00, "readability": 0.58},
        "comments": {"claude": {...}, "chatgpt": {...}, "gemini": {...}}
    }, ...]

用法:
    python -m src.eval.merge_e2e_reviews
    python -m src.eval.merge_e2e_reviews --apply
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS_DIR = ROOT / "data" / "reviews_e2e"
E2E_PATH = ROOT / "data" / "eval_results" / "e2e_queries.json"
GOLD_PATH = ROOT / "data" / "eval_results" / "e2e_gold.json"

EXPECTED_SOURCES = ["claude", "chatgpt", "gemini"]
DIMENSIONS = ["relevance", "completeness", "readability"]


def _extract_score(entry: dict, dim: str) -> int | None:
    """支持两种格式：{dim: {comment, score}} 或 {dim: 4}。"""
    v = entry.get(dim)
    if v is None:
        return None
    if isinstance(v, dict):
        s = v.get("score")
    else:
        s = v
    try:
        s = int(s)
    except (TypeError, ValueError):
        return None
    if not 1 <= s <= 5:
        return None
    return s


def _extract_comment(entry: dict, dim: str) -> str:
    v = entry.get(dim)
    if isinstance(v, dict):
        return str(v.get("comment", "")).strip()
    return ""


def load_reviews() -> dict[str, dict[str, dict]]:
    """返回 {query_id: {source: raw_entry}}。"""
    reviews: dict[str, dict[str, dict]] = {}
    for src in EXPECTED_SOURCES:
        path = REVIEWS_DIR / f"{src}.json"
        if not path.exists():
            print(f"[warn] 缺少 {path}", file=sys.stderr)
            continue
        with path.open("r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            qid = entry.get("query_id")
            if not qid:
                continue
            reviews.setdefault(qid, {})[src] = entry
    return reviews


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not E2E_PATH.exists():
        print(f"[error] {E2E_PATH} not found，先跑 prepare_e2e_queries", file=sys.stderr)
        return 1

    with E2E_PATH.open("r", encoding="utf-8") as f:
        query_records = json.load(f)

    reviews = load_reviews()
    if not reviews:
        print("[error] reviews_e2e 目录空", file=sys.stderr)
        return 1

    gold_records = []
    missing_count = 0
    invalid_score_count = 0

    for rec in query_records:
        qid = rec["query_id"]
        rv = reviews.get(qid, {})
        if len(rv) < len(EXPECTED_SOURCES):
            missing = set(EXPECTED_SOURCES) - set(rv)
            print(f"[warn] {qid} 缺失来源：{missing}")

        per_rater_scores: dict[str, dict[str, int | None]] = {}
        per_rater_comments: dict[str, dict[str, str]] = {}
        for src in EXPECTED_SOURCES:
            entry = rv.get(src, {})
            scores = {}
            comments = {}
            for dim in DIMENSIONS:
                s = _extract_score(entry, dim)
                if s is None and entry:
                    invalid_score_count += 1
                scores[dim] = s
                comments[dim] = _extract_comment(entry, dim)
            per_rater_scores[src] = scores
            per_rater_comments[src] = comments

        mean_by_dim: dict[str, float | None] = {}
        std_by_dim: dict[str, float | None] = {}
        for dim in DIMENSIONS:
            vals = [per_rater_scores[src][dim] for src in EXPECTED_SOURCES
                    if per_rater_scores[src][dim] is not None]
            if not vals:
                mean_by_dim[dim] = None
                std_by_dim[dim] = None
                missing_count += 1
                continue
            mean_by_dim[dim] = round(sum(vals) / len(vals), 3)
            std_by_dim[dim] = round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0

        gold_records.append({
            "query_id": qid,
            "query": rec["query"],
            "per_rater": per_rater_scores,
            "mean": mean_by_dim,
            "std": std_by_dim,
            "comments": per_rater_comments,
        })

    total_cells = len(query_records) * len(EXPECTED_SOURCES) * len(DIMENSIONS)
    print(f"共 {len(query_records)} query × {len(EXPECTED_SOURCES)} rater × {len(DIMENSIONS)} dim = {total_cells} 单元格")
    print(f"  无效/缺失分数：{invalid_score_count}")
    print(f"  完全缺失维度：{missing_count}")

    if not args.apply:
        print("(dry run，加 --apply 写入 e2e_gold.json)")
        return 0

    GOLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLD_PATH.write_text(json.dumps(gold_records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {GOLD_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
