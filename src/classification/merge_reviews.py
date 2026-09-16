"""
Merge multi-LLM review labels into data/labeled_jobs.json.

Vote sources (4):
- GPT-4o-mini initial labels (llm_initial_labels in data/review_sample.json)
- Claude / ChatGPT / Gemini re-labels (data/reviews/*.json)

Rules:
- Clear majority (3/4 or 4/4) -> adopted automatically
- Tie / several categories sharing the top count -> needs a manual decision
  (passed via --resolve hn_XXX:category)

Usage:
    python -m src.classification.merge_reviews
        (dry run: report conflicts, write nothing)

    python -m src.classification.merge_reviews --apply \\
        --resolve hn_1082:data --resolve hn_353:devops
        (adopt majority votes + manual decisions, write back to labeled_jobs.json)
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS_DIR = ROOT / "data" / "reviews"
SAMPLE_PATH = ROOT / "data" / "review_sample.json"
LABELED_PATH = ROOT / "data" / "labeled_jobs.json"

MULTI_LLM_SOURCE = "llm-gpt-4o-mini + multi-llm-vote"
HUMAN_FINAL_SOURCE = "llm-gpt-4o-mini + multi-llm-vote + human-final"


def load_votes() -> dict[str, dict[str, str]]:
    """Return {job_id: {source_name: category}}."""
    votes: dict[str, dict[str, str]] = {}

    with SAMPLE_PATH.open("r", encoding="utf-8") as f:
        sample = json.load(f)
    for entry in sample["llm_initial_labels"]:
        votes.setdefault(entry["job_id"], {})["gpt-4o-mini"] = entry["category"]

    for review_file in sorted(REVIEWS_DIR.glob("*.json")):
        source = review_file.stem
        with review_file.open("r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            votes.setdefault(entry["job_id"], {})[source] = entry["category"]

    return votes


def tally(job_votes: dict[str, str]):
    """Return (winner|None, [(category, count), ...]). winner=None means a tie."""
    counter = Counter(job_votes.values())
    ranked = counter.most_common()
    if not ranked:
        return None, []
    top = ranked[0][1]
    winners = [cat for cat, c in ranked if c == top]
    return (winners[0] if len(winners) == 1 else None), ranked


def parse_resolves(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        if ":" not in item:
            raise SystemExit(f"invalid --resolve {item!r}, expected job_id:category")
        jid, cat = item.split(":", 1)
        out[jid.strip()] = cat.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write back to labeled_jobs.json")
    ap.add_argument("--resolve", action="append", default=[], help="manual tie break: job_id:category")
    args = ap.parse_args()

    votes = load_votes()
    if not votes:
        print("[error] no votes found", file=sys.stderr)
        return 1

    resolves = parse_resolves(args.resolve)
    decisions: dict[str, tuple[str, str]] = {}
    conflicts: list[tuple[str, list]] = []

    n_sources = len(next(iter(votes.values())))
    print(f"{len(votes)} samples, {n_sources} vote sources")
    print("=" * 78)

    unanimous = 0
    changes = 0
    for job_id in sorted(votes, key=lambda x: int(x.split("_")[1])):
        jv = votes[job_id]
        winner, ranked = tally(jv)
        ranked_str = ", ".join(f"{c}={n}" for c, n in ranked)
        gpt_label = jv.get("gpt-4o-mini", "?")

        if winner:
            if len(ranked) == 1:
                unanimous += 1
            if winner != gpt_label:
                changes += 1
                print(f"[changed]  {job_id:<10}  {gpt_label} -> {winner}  ({ranked_str})")
            decisions[job_id] = (winner, MULTI_LLM_SOURCE)
        else:
            if job_id in resolves:
                decisions[job_id] = (resolves[job_id], HUMAN_FINAL_SOURCE)
                print(f"[resolved] {job_id:<10}  manual -> {resolves[job_id]}  ({ranked_str})")
            else:
                conflicts.append((job_id, ranked))
                print(f"[conflict] {job_id:<10}  needs manual decision  ({ranked_str})")

    print("=" * 78)
    print(f"unanimous={unanimous}  changed by majority={changes}  unresolved={len(conflicts)}")

    if conflicts:
        print()
        print("Unresolved conflicts. Re-run with these extra arguments:")
        for jid, _ in conflicts:
            print(f"    --resolve {jid}:<category>")
        return 2

    if not args.apply:
        print("(dry run; pass --apply to write back to labeled_jobs.json)")
        return 0

    with LABELED_PATH.open("r", encoding="utf-8") as f:
        labeled = json.load(f)

    updated = 0
    for job in labeled:
        jid = job["job_id"]
        if jid not in decisions:
            continue
        new_cat, new_src = decisions[jid]
        job["category"] = new_cat
        job["label_source"] = new_src
        updated += 1

    with LABELED_PATH.open("w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)

    print(f"\nWrote {LABELED_PATH}, updated {updated} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
