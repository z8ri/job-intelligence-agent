"""
Manual spot-check of the initial LLM labels in data/labeled_jobs.json.

Randomly samples from the labeled file (default 20% = 24 jobs) and shows each
job's title/tags/description plus the LLM-assigned category, so a human can
quickly confirm or override it.

Usage:
    python -m src.classification.review              # review 24 jobs (default)
    python -m src.classification.review --sample 40  # review 40 jobs
    python -m src.classification.review --all        # go through all 120 jobs
    python -m src.classification.review --seed 42    # fixed random seed

Interactive keys:
    0-6       override with the corresponding category
    Enter     keep the LLM label (counts as human-confirmed)
    s         skip this job (label_source unchanged)
    q         save immediately and quit

Every job that is changed or confirmed gets label_source = "llm-gpt-4o-mini + human-review".
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
    """Return (changed, confirmed, skipped) counts."""
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
