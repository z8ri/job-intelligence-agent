"""
§7.3 分类准确率测试集 — 分层抽样

从 MySQL jobs 表排除 120 条 labeled_jobs（训练集），按分类器预测的 category
字段分层抽样，每类约 8-9 条，共 60 条。

用法:
    python -m src.eval.sample_class_test_set                  # 默认 per-class=8, seed=42
    python -m src.eval.sample_class_test_set --per-class 10
    python -m src.eval.sample_class_test_set --seed 123

输出:
    data/eval_results/classification_test_set.json
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from src.db.database import get_connection

ROOT = Path(__file__).resolve().parent.parent.parent
LABELED_PATH = ROOT / "data" / "labeled_jobs.json"
OUT_PATH = ROOT / "data" / "eval_results" / "classification_test_set.json"

CATEGORIES = ["backend", "frontend", "data", "devops", "fullstack", "mobile", "management"]


def load_train_job_ids() -> set[str]:
    with LABELED_PATH.open("r", encoding="utf-8") as f:
        labeled = json.load(f)
    return {j["job_id"] for j in labeled}


def fetch_jobs_by_category(exclude_ids: set[str]) -> dict[str, list[dict]]:
    """按 category 分组取回所有可抽职位（已排除训练集）。"""
    groups: dict[str, list[dict]] = defaultdict(list)
    conn = get_connection()
    try:
        placeholders = ",".join(["%s"] * len(CATEGORIES))
        sql = (
            f"SELECT job_id, company, title, description, category "
            f"FROM jobs WHERE category IN ({placeholders})"
        )
        with conn.cursor() as cur:
            cur.execute(sql, CATEGORIES)
            rows = cur.fetchall()

        job_ids = [r["job_id"] for r in rows if r["job_id"] not in exclude_ids]
        if not job_ids:
            return groups

        tag_map: dict[str, list[str]] = defaultdict(list)
        for chunk_start in range(0, len(job_ids), 1000):
            chunk = job_ids[chunk_start:chunk_start + 1000]
            ph = ",".join(["%s"] * len(chunk))
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT job_id, tag FROM job_tags WHERE job_id IN ({ph})",
                    chunk,
                )
                for t in cur.fetchall():
                    tag_map[t["job_id"]].append(t["tag"])
    finally:
        conn.close()

    for r in rows:
        if r["job_id"] in exclude_ids:
            continue
        r["tags"] = tag_map.get(r["job_id"], [])
        groups[r["category"]].append(r)
    return groups


def stratified_sample(groups: dict[str, list[dict]], per_class: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    selected: list[dict] = []
    for cat in CATEGORIES:
        pool = groups.get(cat, [])
        k = min(per_class, len(pool))
        if k < per_class:
            print(f"[warn] category '{cat}' only has {len(pool)} candidates (< {per_class})", file=sys.stderr)
        selected.extend(rng.sample(pool, k))
    return selected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-class", type=int, default=8, help="samples per category (default 8 → 56 total)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    exclude = load_train_job_ids()
    print(f"排除训练集 {len(exclude)} 条")

    groups = fetch_jobs_by_category(exclude)
    for cat in CATEGORIES:
        print(f"  {cat:<12} 可抽 {len(groups.get(cat, []))}")

    sampled = stratified_sample(groups, args.per_class, args.seed)
    print(f"\n共抽样 {len(sampled)} 条")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = [
        {
            "job_id": j["job_id"],
            "company": j["company"],
            "title": j["title"],
            "tags": j["tags"],
            "description": j["description"],
            "predicted_category": j["category"],
        }
        for j in sampled
    ]
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
