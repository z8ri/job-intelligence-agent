"""
Section 7.2 preference-extraction accuracy: merge the three LLMs' independently
extracted preference JSON into gold.

Reads data/reviews_pref/{claude,chatgpt,gemini}.json
(format: [{"query_id": "q01", "preferences": {...}}, ...])

Field-level majority vote:
- scalar fields (target_salary / remote_preference / preferred_location / preferred_category)
  - 3/3 agree -> unanimous
  - 2/3 agree -> majority
  - 1-1-1 -> disputed (resolved with --resolve q01.field=value)
- list fields (description_keywords / desired_tags): keep elements mentioned by >=2 raters
- weight_adjustments: majority vote on the importance label of each field separately
- hard_filters: gold=[] if >=2 raters gave an empty list; otherwise the union

Usage:
    python -m src.eval.merge_pref_reviews
    python -m src.eval.merge_pref_reviews --apply
    python -m src.eval.merge_pref_reviews --apply --resolve q01.target_salary=150000

Output:
    data/eval_results/pref_extraction_gold.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS_DIR = ROOT / "data" / "reviews_pref"
TEST_QUERIES_PATH = ROOT / "data" / "test_queries.json"
GOLD_PATH = ROOT / "data" / "eval_results" / "pref_extraction_gold.json"

EXPECTED_SOURCES = ["claude", "chatgpt", "gemini"]

SCALAR_FIELDS = ["target_salary", "remote_preference", "preferred_location", "preferred_category"]
LIST_FIELDS = ["description_keywords", "desired_tags"]


def load_reviews() -> dict[str, dict[str, dict]]:
    """Return {query_id: {source: preferences}}."""
    reviews: dict[str, dict[str, dict]] = {}
    for src in EXPECTED_SOURCES:
        path = REVIEWS_DIR / f"{src}.json"
        if not path.exists():
            print(f"[warn] missing {path}", file=sys.stderr)
            continue
        with path.open("r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            qid = entry["query_id"]
            prefs = entry["preferences"]
            reviews.setdefault(qid, {})[src] = prefs
    return reviews


def normalize_scalar(val):
    """Unify None/empty values and normalize case so votes compare cleanly."""
    if val is None or val == "":
        return None
    if isinstance(val, str):
        return val.strip().lower() or None
    return val


def vote_scalar(values: list):
    """Three-way vote on a scalar field. Returns (winner, verdict, ranked)."""
    normed = [normalize_scalar(v) for v in values]
    counter = Counter(normed)
    ranked = counter.most_common()
    top = ranked[0][1]
    winners = [v for v, n in ranked if n == top]

    if len(ranked) == 1:
        return winners[0], "unanimous", ranked
    if len(winners) == 1:
        return winners[0], "majority", ranked
    return None, "disputed", ranked


def normalize_list(vals):
    """Normalize a list field: lowercase + strip + dedupe; None counts as []."""
    if not vals:
        return set()
    return {str(v).strip().lower() for v in vals if v}


def vote_list(values: list[list]):
    """For list fields, keep the elements mentioned by >=2 raters."""
    sets = [normalize_list(v) for v in values]
    all_elements: Counter = Counter()
    for s in sets:
        for e in s:
            all_elements[e] += 1
    kept = sorted([e for e, c in all_elements.items() if c >= 2])
    return kept if kept else None


def vote_weight_adjustments(values: list[dict]):
    """weight_adjustments: majority vote on each field's importance label separately."""
    from collections import defaultdict
    per_field: dict[str, list[str]] = defaultdict(list)
    for v in values:
        if not isinstance(v, dict):
            continue
        for field, importance in v.items():
            per_field[field].append(importance)

    gold: dict[str, str] = {}
    for field, importances in per_field.items():
        if len(importances) < 2:  # minority opinion, not included in gold
            continue
        counter = Counter(importances)
        top_count = counter.most_common(1)[0][1]
        winners = [imp for imp, c in counter.items() if c == top_count]
        if len(winners) == 1:
            gold[field] = winners[0]
    return gold


def vote_hard_filters(values: list):
    """hard_filters: gold=[] if >=2 raters gave an empty list, otherwise the union. Rare case, kept simple."""
    empties = sum(1 for v in values if not v)
    if empties >= 2:
        return []
    merged = []
    seen = set()
    for v in values:
        if isinstance(v, list):
            for item in v:
                key = json.dumps(item, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    merged.append(item)
    return merged


def parse_resolves(items: list[str]) -> dict:
    """--resolve q01.target_salary=150000 -> {q01: {target_salary: 150000}}"""
    out: dict[str, dict] = {}
    for item in items:
        if "=" not in item or "." not in item.split("=")[0]:
            raise SystemExit(f"invalid --resolve {item!r}, expected q01.field=value")
        lhs, rhs = item.split("=", 1)
        qid, field = lhs.split(".", 1)
        # Try to parse as JSON; fall back to a plain string
        try:
            val = json.loads(rhs)
        except json.JSONDecodeError:
            val = rhs
        out.setdefault(qid.strip(), {})[field.strip()] = val
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--resolve", action="append", default=[])
    args = ap.parse_args()

    if not TEST_QUERIES_PATH.exists():
        print(f"[error] {TEST_QUERIES_PATH} not found", file=sys.stderr)
        return 1

    with TEST_QUERIES_PATH.open("r", encoding="utf-8") as f:
        queries = json.load(f)

    reviews = load_reviews()
    if not reviews:
        print("[error] reviews_pref directory is empty", file=sys.stderr)
        return 1

    resolves = parse_resolves(args.resolve)

    gold_records = []
    disputed_fields: list[tuple[str, str, list]] = []
    stats = Counter()

    for q in queries:
        qid = q["id"]
        rv = reviews.get(qid, {})
        if len(rv) < len(EXPECTED_SOURCES):
            missing = set(EXPECTED_SOURCES) - set(rv)
            print(f"[warn] {qid} missing: {missing}")

        gold = {}
        field_verdicts = {}

        # Scalar fields
        for f in SCALAR_FIELDS:
            vals = [rv.get(src, {}).get(f) for src in EXPECTED_SOURCES]
            winner, verdict, ranked = vote_scalar(vals)
            if verdict == "disputed":
                if qid in resolves and f in resolves[qid]:
                    gold[f] = resolves[qid][f]
                    field_verdicts[f] = "human_resolved"
                    stats["human_resolved"] += 1
                else:
                    disputed_fields.append((qid, f, ranked))
                    gold[f] = None
                    field_verdicts[f] = "disputed"
                    stats["disputed"] += 1
            else:
                # target_salary is an int; normalize_scalar may have turned the winner into a lowercase str, so restore it
                if f == "target_salary" and winner is not None:
                    # Find the matching original value
                    for v in vals:
                        if v is not None and normalize_scalar(v) == winner:
                            winner = v
                            break
                gold[f] = winner
                field_verdicts[f] = verdict
                stats[verdict] += 1

        # List fields
        for f in LIST_FIELDS:
            vals = [rv.get(src, {}).get(f) for src in EXPECTED_SOURCES]
            gold[f] = vote_list(vals)
            field_verdicts[f] = "list_union≥2"
            stats["list"] += 1

        # weight_adjustments
        wa_vals = [rv.get(src, {}).get("weight_adjustments", {}) for src in EXPECTED_SOURCES]
        gold["weight_adjustments"] = vote_weight_adjustments(wa_vals)
        field_verdicts["weight_adjustments"] = "wa_vote"

        # hard_filters
        hf_vals = [rv.get(src, {}).get("hard_filters", []) for src in EXPECTED_SOURCES]
        gold["hard_filters"] = vote_hard_filters(hf_vals)
        field_verdicts["hard_filters"] = "hf_merge"

        gold_records.append({
            "query_id": qid,
            "query": q["query"],
            "gold_preferences": gold,
            "field_verdicts": field_verdicts,
            "raw_votes": rv,
        })

    print(f"{len(queries)} queries x {len(SCALAR_FIELDS)} scalar fields")
    print(f"  unanimous {stats['unanimous']}  majority {stats['majority']}  disputed {stats['disputed']}  human-resolved {stats['human_resolved']}")

    if disputed_fields:
        print()
        print("Unresolved disputes:")
        for qid, f, ranked in disputed_fields:
            r_str = ", ".join(f"{v}={n}" for v, n in ranked)
            print(f"  {qid}.{f}: {r_str}")
            print(f"    add: --resolve {qid}.{f}=<value>")
        if not args.apply:
            print()
            print("(dry run)")
        return 2

    if not args.apply:
        print("(dry run; add --apply to write gold)")
        return 0

    GOLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLD_PATH.write_text(json.dumps(gold_records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWritten to {GOLD_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
