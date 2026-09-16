"""
Section 7.3 classification accuracy test set: stratified sampling.

Excludes the 120 labeled_jobs (training set) from the MySQL jobs table, then
samples stratified by the classifier's predicted category, about 8-9 per class
for roughly 60 in total.

Usage:
    python -m src.eval.sample_class_test_set                  # default per-class=8, seed=42
    python -m src.eval.sample_class_test_set --per-class 10
    python -m src.eval.sample_class_test_set --seed 123

Output:
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
    """Fetch all sampleable jobs grouped by category (training set excluded)."""
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
    ap.add_argument("--per-class", type=int, default=8, help="samples per category (default 8 -> 56 total)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    exclude = load_train_job_ids()
    print(f"Excluding {len(exclude)} training-set jobs")

    groups = fetch_jobs_by_category(exclude)
    for cat in CATEGORIES:
        print(f"  {cat:<12} available {len(groups.get(cat, []))}")

    sampled = stratified_sample(groups, args.per_class, args.seed)
    print(f"\nSampled {len(sampled)} jobs in total")

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
    print(f"Written to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
