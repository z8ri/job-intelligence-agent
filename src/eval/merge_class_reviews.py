"""
Section 7.3 classification accuracy: merge the three LLMs' independent labels into gold.

Reads data/reviews_class/{claude,chatgpt,gemini}.json, takes a majority vote
per job_id and writes the gold set.

Rules:
- 3/3 agree -> unanimous
- 2/3 agree -> majority
- 1-1-1 split -> disputed (needs a --resolve job_id:category decision)

Usage:
    python -m src.eval.merge_class_reviews                  # dry run, reports conflicts
    python -m src.eval.merge_class_reviews --apply          # write gold to disk
    python -m src.eval.merge_class_reviews --apply --resolve hn_123:backend

Output:
    data/eval_results/classification_gold.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS_DIR = ROOT / "data" / "reviews_class"
TEST_SET_PATH = ROOT / "data" / "eval_results" / "classification_test_set.json"
GOLD_PATH = ROOT / "data" / "eval_results" / "classification_gold.json"

EXPECTED_SOURCES = ["claude", "chatgpt", "gemini"]


def load_votes() -> dict[str, dict[str, str]]:
    """Return {job_id: {source: category}}."""
    votes: dict[str, dict[str, str]] = {}

    for src in EXPECTED_SOURCES:
        path = REVIEWS_DIR / f"{src}.json"
        if not path.exists():
            print(f"[warn] missing {path}", file=sys.stderr)
            continue
        with path.open("r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            votes.setdefault(entry["job_id"], {})[src] = entry["category"]

    return votes


def tally(job_votes: dict[str, str]):
    """Return (winner|None, ranked_list)."""
    counter = Counter(job_votes.values())
    ranked = counter.most_common()
    if not ranked:
        return None, []
    top_count = ranked[0][1]
    winners = [c for c, n in ranked if n == top_count]
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
    ap.add_argument("--apply", action="store_true", help="write gold to disk")
    ap.add_argument("--resolve", action="append", default=[], help="manual tie break: job_id:category")
    args = ap.parse_args()

    if not TEST_SET_PATH.exists():
        print(f"[error] {TEST_SET_PATH} not found", file=sys.stderr)
        return 1

    with TEST_SET_PATH.open("r", encoding="utf-8") as f:
        test_set = json.load(f)

    votes = load_votes()
    if not votes:
        print("[error] no JSON in the reviews directory; collect the three LLM answers first", file=sys.stderr)
        return 1

    resolves = parse_resolves(args.resolve)

    unanimous = 0
    majority = 0
    disputed: list[tuple[str, list]] = []
    decisions: dict[str, tuple[str, str, list]] = {}

    print(f"{len(test_set)} test samples in total")
    print("=" * 80)

    for job in test_set:
        jid = job["job_id"]
        jv = votes.get(jid, {})
        if len(jv) < len(EXPECTED_SOURCES):
            missing = set(EXPECTED_SOURCES) - set(jv)
            print(f"[warn] {jid} missing sources: {missing}")
        winner, ranked = tally(jv)
        ranked_str = ", ".join(f"{c}={n}" for c, n in ranked)

        if winner:
            if len(ranked) == 1:
                unanimous += 1
                verdict = "unanimous"
            else:
                majority += 1
                verdict = "majority"
            decisions[jid] = (winner, verdict, ranked)
        else:
            if jid in resolves:
                decisions[jid] = (resolves[jid], "human_resolved", ranked)
                print(f"[resolved] {jid:<10} human -> {resolves[jid]}  ({ranked_str})")
            else:
                disputed.append((jid, ranked))
                print(f"[disputed] {jid:<10} 1-1-1  ({ranked_str})")

    print("=" * 80)
    print(f"unanimous {unanimous}  majority {majority}  disputed {len(disputed)}")

    if disputed:
        print()
        print("Unresolved disputes. Re-run with:")
        for jid, _ in disputed:
            print(f"    --resolve {jid}:<category>")
        return 2

    if not args.apply:
        print("(dry run; add --apply to write gold)")
        return 0

    gold = []
    for job in test_set:
        jid = job["job_id"]
        cat, verdict, ranked = decisions[jid]
        gold.append({
            "job_id": jid,
            "predicted_category": job["predicted_category"],
            "gold_category": cat,
            "verdict": verdict,
            "votes": dict(ranked),
        })

    GOLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLD_PATH.write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWritten to {GOLD_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
