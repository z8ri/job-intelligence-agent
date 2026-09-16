"""
批量预测全库职位类别并回写 DB。

- 120 条训练集（labeled_jobs.json）保留 gold label
- 其余全部走 Rocchio 分类器预测
- UPDATE jobs SET category = ? WHERE job_id = ?

用法：
    python -m src.classification.batch_predict              # dry run，只打印分布
    python -m src.classification.batch_predict --apply      # 真正写回 DB
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from src.classification.classifier import CATEGORIES, JobClassifier
from src.db.database import get_connection, load_candidates

ROOT = Path(__file__).resolve().parent.parent.parent
LABELED_PATH = ROOT / "data" / "labeled_jobs.json"
MODEL_DIR = ROOT / "models" / "classifier"
CATEGORY_SCORES_PATH = ROOT / "data" / "category_scores.json"


def load_gold_labels() -> dict[str, str]:
    """返回 {job_id: category} 的 gold label 映射。"""
    with LABELED_PATH.open("r", encoding="utf-8") as f:
        labeled = json.load(f)
    return {job["job_id"]: job["category"] for job in labeled}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写回 DB")
    args = ap.parse_args()

    clf = JobClassifier.load(str(MODEL_DIR))
    gold = load_gold_labels()
    print(f"gold label: {len(gold)} 条")

    jobs = load_candidates()
    print(f"DB 候选: {len(jobs)} 条")
    if not jobs:
        print("[error] DB 无数据", file=sys.stderr)
        return 1

    texts: list[str] = []
    job_ids_to_predict: list[str] = []
    assignments: dict[str, tuple[str, str]] = {}  # job_id -> (category, source)
    scores_map: dict[str, dict[str, float]] = {}  # job_id -> {cat: cosine}

    for job in jobs:
        jid = job["job_id"]
        if jid in gold:
            assignments[jid] = (gold[jid], "gold")
            # gold 条目赋 one-hot：gold 类=1.0，其他=0.0
            scores_map[jid] = {c: (1.0 if c == gold[jid] else 0.0) for c in CATEGORIES}
            continue
        texts.append(JobClassifier.prepare_text(job))
        job_ids_to_predict.append(jid)

    if texts:
        preds = clf.predict_batch(texts)
        for jid, (cat, scores) in zip(job_ids_to_predict, preds):
            assignments[jid] = (cat, "predicted")
            # 全 7 类补齐：训练时缺失类别保 0
            scores_map[jid] = {c: float(scores.get(c, 0.0)) for c in CATEGORIES}

    dist = Counter(cat for cat, _ in assignments.values())
    gold_dist = Counter(cat for jid, (cat, src) in assignments.items() if src == "gold")
    pred_dist = Counter(cat for jid, (cat, src) in assignments.items() if src == "predicted")

    print()
    print(f"gold   {dict(sorted(gold_dist.items()))}")
    print(f"pred   {dict(sorted(pred_dist.items()))}")
    print(f"total  {dict(sorted(dist.items()))}")

    if not args.apply:
        print("\n(dry run，加 --apply 写回 DB)")
        return 0

    rows = [(cat, jid) for jid, (cat, _) in assignments.items()]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany("UPDATE jobs SET category = %s WHERE job_id = %s", rows)
        conn.commit()
    finally:
        conn.close()

    with CATEGORY_SCORES_PATH.open("w", encoding="utf-8") as f:
        json.dump(scores_map, f, ensure_ascii=False)

    print(f"\n已更新 {len(rows)} 条 jobs.category")
    print(f"已写入 {CATEGORY_SCORES_PATH} ({len(scores_map)} 条 7 类 cosine)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
