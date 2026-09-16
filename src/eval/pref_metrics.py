"""
Section 7.2 preference-extraction accuracy: metric computation.

Reads data/eval_results/pref_extraction_gold.json (majority-vote gold from the
three LLMs) and data/eval_results/pref_system_output.json (our system's
gpt-4o-mini output) and computes per-field accuracy.

Field matching rules:
- target_salary: match if within $10k (None vs None also matches)
- preferred_location: case-insensitive string equality
- remote_preference / preferred_category: exact equality
- desired_tags / description_keywords: match if Jaccard >= 0.6 (None vs None matches)
- weight_adjustments: exact dict equality (keys and values)
- hard_filters: ignored (almost always empty)

Usage:
    python -m src.eval.pref_metrics

Outputs:
    data/eval_results/pref_extraction_metrics.json
    data/eval_results/pref_extraction_report.md
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_PATH = ROOT / "data" / "eval_results" / "pref_extraction_gold.json"
SYSTEM_PATH = ROOT / "data" / "eval_results" / "pref_system_output.json"
METRICS_PATH = ROOT / "data" / "eval_results" / "pref_extraction_metrics.json"
REPORT_PATH = ROOT / "data" / "eval_results" / "pref_extraction_report.md"

EVAL_FIELDS = [
    "target_salary",
    "preferred_location",
    "remote_preference",
    "preferred_category",
    "desired_tags",
    "description_keywords",
    "weight_adjustments",
]

SALARY_TOL = 10000
JACCARD_MIN = 0.6


def norm_list(v) -> set[str]:
    if not v:
        return set()
    return {str(x).strip().lower() for x in v if x}


def match_salary(gold, sys_val) -> bool:
    if gold is None and sys_val is None:
        return True
    if gold is None or sys_val is None:
        return False
    try:
        return abs(int(gold) - int(sys_val)) <= SALARY_TOL
    except (ValueError, TypeError):
        return False


def match_scalar_str(gold, sys_val) -> bool:
    g = (gold or "").strip().lower() if isinstance(gold, str) else gold
    s = (sys_val or "").strip().lower() if isinstance(sys_val, str) else sys_val
    return g == s


def match_jaccard(gold, sys_val) -> bool:
    g = norm_list(gold)
    s = norm_list(sys_val)
    if not g and not s:
        return True
    if not g or not s:
        return False
    inter = len(g & s)
    union = len(g | s)
    return (inter / union) >= JACCARD_MIN if union > 0 else True


def match_weight_adj(gold, sys_val) -> bool:
    if not gold and not sys_val:
        return True
    return dict(gold or {}) == dict(sys_val or {})


MATCHERS = {
    "target_salary": match_salary,
    "preferred_location": match_scalar_str,
    "remote_preference": match_scalar_str,
    "preferred_category": match_scalar_str,
    "desired_tags": match_jaccard,
    "description_keywords": match_jaccard,
    "weight_adjustments": match_weight_adj,
}


def main() -> int:
    for path in [GOLD_PATH, SYSTEM_PATH]:
        if not path.exists():
            print(f"[error] {path} not found", file=sys.stderr)
            return 1

    with GOLD_PATH.open("r", encoding="utf-8") as f:
        gold_records = {r["query_id"]: r for r in json.load(f)}
    with SYSTEM_PATH.open("r", encoding="utf-8") as f:
        system_records = {r["query_id"]: r for r in json.load(f)}

    shared_ids = sorted(set(gold_records) & set(system_records))
    n = len(shared_ids)
    if n == 0:
        print("[error] gold and system share no query_id", file=sys.stderr)
        return 1

    per_field_correct: dict[str, int] = {f: 0 for f in EVAL_FIELDS}
    per_query: list[dict] = []

    for qid in shared_ids:
        gold = gold_records[qid]["gold_preferences"]
        sys_prefs = system_records[qid].get("preferences", {})
        field_results = {}
        for f in EVAL_FIELDS:
            matcher = MATCHERS[f]
            ok = matcher(gold.get(f), sys_prefs.get(f))
            field_results[f] = ok
            if ok:
                per_field_correct[f] += 1
        per_query.append({
            "query_id": qid,
            "query": gold_records[qid]["query"],
            "gold": gold,
            "system": sys_prefs,
            "field_results": field_results,
        })

    field_acc = {f: per_field_correct[f] / n for f in EVAL_FIELDS}
    macro = sum(field_acc.values()) / len(EVAL_FIELDS)
    all_correct = sum(1 for pq in per_query if all(pq["field_results"].values()))

    metrics = {
        "total_queries": n,
        "field_accuracy": field_acc,
        "macro_field_accuracy": macro,
        "all_fields_correct": all_correct,
        "all_fields_correct_ratio": all_correct / n,
    }

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Preference Extraction Accuracy Report (Section 7.2)",
        "",
        f"- Test queries: **{n}** (all of data/test_queries.json)",
        f"- Gold source: independent extraction by Claude / ChatGPT / Gemini + field-level majority vote",
        f"- System: gpt-4o-mini (src/llm/query_understanding.py)",
        "",
        "## Per-field accuracy",
        "",
        "| Field | Match rule | accuracy |",
        "|---|---|---|",
    ]
    rules = {
        "target_salary": f"within ${SALARY_TOL:,}",
        "preferred_location": "case-insensitive string equality",
        "remote_preference": "exact equality",
        "preferred_category": "exact equality",
        "desired_tags": f"Jaccard ≥ {JACCARD_MIN}",
        "description_keywords": f"Jaccard ≥ {JACCARD_MIN}",
        "weight_adjustments": "exact dict equality",
    }
    for f in EVAL_FIELDS:
        lines.append(f"| {f} | {rules[f]} | {field_acc[f]:.3f} |")

    lines.extend([
        "",
        f"- **Macro-field accuracy: {macro:.3f}**",
        f"- All fields correct at once: {all_correct}/{n} ({all_correct/n:.3f})",
        "",
        "## Failure cases (first 10)",
        "",
    ])

    failures = [pq for pq in per_query if not all(pq["field_results"].values())]
    for pq in failures[:10]:
        wrong_fields = [f for f, ok in pq["field_results"].items() if not ok]
        lines.append(f"- **{pq['query_id']}**: `{pq['query']}`")
        for f in wrong_fields:
            lines.append(f"  - `{f}` — gold: `{json.dumps(pq['gold'].get(f), ensure_ascii=False)}` vs sys: `{json.dumps(pq['system'].get(f), ensure_ascii=False)}`")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Macro-field accuracy: {macro:.3f}")
    for f in EVAL_FIELDS:
        print(f"  {f:<22} {field_acc[f]:.3f}")
    print(f"Written:")
    print(f"  - {METRICS_PATH}")
    print(f"  - {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
