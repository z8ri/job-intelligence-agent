"""
§7.2 偏好提取准确率 — 指标计算

读取 data/eval_results/pref_extraction_gold.json（三家多数投票的 gold）
和 data/eval_results/pref_system_output.json（我们系统 gpt-4o-mini 的输出），
按字段算准确率。

字段匹配规则：
- target_salary：误差 ≤ $10k 算 match（None 对 None 也算 match）
- preferred_location：小写后字符串相等
- remote_preference / preferred_category：精确相等
- desired_tags / description_keywords：Jaccard ≥ 0.6 算 match（None 对 None match）
- weight_adjustments：dict 精确相等（键和值都相等）
- hard_filters：忽略（大多数为空）

用法:
    python -m src.eval.pref_metrics

输出:
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
        print("[error] gold 与 system 无共同 query_id", file=sys.stderr)
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
        "# 偏好提取准确率评估报告 (§7.2)",
        "",
        f"- 测试查询：**{n}** 条（data/test_queries.json 全集）",
        f"- Gold 来源：Claude / ChatGPT / Gemini 三家独立提取 + 字段粒度多数投票",
        f"- 系统：gpt-4o-mini（src/llm/query_understanding.py）",
        "",
        "## 字段级准确率",
        "",
        "| 字段 | 匹配规则 | accuracy |",
        "|---|---|---|",
    ]
    rules = {
        "target_salary": f"误差 ≤ ${SALARY_TOL:,}",
        "preferred_location": "小写字符串相等",
        "remote_preference": "精确相等",
        "preferred_category": "精确相等",
        "desired_tags": f"Jaccard ≥ {JACCARD_MIN}",
        "description_keywords": f"Jaccard ≥ {JACCARD_MIN}",
        "weight_adjustments": "dict 精确相等",
    }
    for f in EVAL_FIELDS:
        lines.append(f"| {f} | {rules[f]} | {field_acc[f]:.3f} |")

    lines.extend([
        "",
        f"- **Macro-field accuracy: {macro:.3f}**",
        f"- 全字段同时正确：{all_correct}/{n} ({all_correct/n:.3f})",
        "",
        "## 失败案例（前 10 条）",
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
    print(f"已写入:")
    print(f"  - {METRICS_PATH}")
    print(f"  - {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
