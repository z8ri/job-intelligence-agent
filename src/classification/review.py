"""
人工抽查 data/labeled_jobs.json 中的 LLM 初标结果。

从标注文件里随机采样（默认 20% = 24 条），逐条展示 title/tags/description
和 LLM 给的 category，让人工快速确认或覆盖。

用法:
    python -m src.classification.review              # 默认抽查 24 条
    python -m src.classification.review --sample 40  # 抽查 40 条
    python -m src.classification.review --all        # 过一遍全部 120 条
    python -m src.classification.review --seed 42    # 固定随机种子

交互键:
    0-6       选对应类别覆盖
    Enter     保留 LLM 判断（视为人工已确认）
    s         跳过此条（label_source 不变）
    q         立即保存并退出

每条被修改或确认的 job,label_source 更新为 "llm-gpt-4o-mini + human-review"。
"""

import argparse
import json
import random
import sys
from pathlib import Path

LABELED_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "labeled_jobs.json"

CATEGORIES = ["backend", "frontend", "data", "devops", "fullstack", "mobile", "management"]
DESC_PREVIEW_CHARS = 500
REVIEWED_SOURCE = "llm-gpt-4o-mini + human-review"


def load_labeled(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_labeled(labeled: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)


def format_one(job: dict, idx: int, total: int) -> str:
    tags = ", ".join(job.get("tags") or []) or "(no tags)"
    desc = (job.get("description") or "").strip().replace("\n", " ")
    if len(desc) > DESC_PREVIEW_CHARS:
        desc = desc[:DESC_PREVIEW_CHARS].rstrip() + "..."
    llm_cat = job.get("category", "?")

    lines = [
        "",
        "=" * 78,
        f"[{idx}/{total}]  job_id={job.get('job_id')}  company={job.get('company')!r}",
        "-" * 78,
        f"Title: {job.get('title')}",
        f"Tags:  {tags}",
        f"Desc:  {desc}",
        "-" * 78,
        f"LLM category: {llm_cat}",
        "",
    ]
    return "\n".join(lines)


def prompt_menu() -> str:
    opts = "  ".join(f"[{i}]{c}" for i, c in enumerate(CATEGORIES))
    return f"  {opts}\n  [Enter]keep  [s]skip  [q]quit-save\n> "


def review(labeled: list[dict], indices: list[int]) -> tuple[int, int, int]:
    """返回 (changed, confirmed, skipped) 计数。"""
    changed = 0
    confirmed = 0
    skipped = 0
    total = len(indices)

    for i, pos in enumerate(indices, start=1):
        job = labeled[pos]
        print(format_one(job, i, total))

        while True:
            try:
                answer = input(prompt_menu()).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  -> saving and exiting...")
                return changed, confirmed, skipped

            if answer == "q":
                return changed, confirmed, skipped
            if answer == "s":
                skipped += 1
                print("  -> skipped")
                break
            if answer == "":
                job["label_source"] = REVIEWED_SOURCE
                confirmed += 1
                print(f"  -> kept: {job['category']}")
                break
            if answer.isdigit() and 0 <= int(answer) < len(CATEGORIES):
                new_cat = CATEGORIES[int(answer)]
                old_cat = job.get("category")
                job["category"] = new_cat
                job["label_source"] = REVIEWED_SOURCE
                if new_cat != old_cat:
                    changed += 1
                    print(f"  -> changed: {old_cat} -> {new_cat}")
                else:
                    confirmed += 1
                    print(f"  -> kept: {new_cat}")
                break
            print(f"  ! invalid input {answer!r}, try again")

    return changed, confirmed, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Human review of LLM-labeled jobs")
    parser.add_argument("--sample", type=int, default=24, help="review N random jobs (default 24)")
    parser.add_argument("--all", action="store_true", help="review all jobs in file")
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducible sampling")
    args = parser.parse_args()

    if not LABELED_PATH.exists():
        print(f"[error] {LABELED_PATH} not found. Run auto_label.py first.", file=sys.stderr)
        return 1

    labeled = load_labeled(LABELED_PATH)
    n = len(labeled)
    if n == 0:
        print("[error] empty labeled file", file=sys.stderr)
        return 1

    if args.all:
        indices = list(range(n))
    else:
        k = min(args.sample, n)
        if args.seed is not None:
            random.seed(args.seed)
        indices = sorted(random.sample(range(n), k))

    print(f"Reviewing {len(indices)}/{n} jobs from {LABELED_PATH.name}")
    print("(progress saved on quit or completion)")

    try:
        changed, confirmed, skipped = review(labeled, indices)
    finally:
        save_labeled(labeled, LABELED_PATH)

    print()
    print("=" * 78)
    print(f"Done. changed={changed}  confirmed={confirmed}  skipped={skipped}")
    print(f"Saved to {LABELED_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
