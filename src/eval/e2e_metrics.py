"""
§7.6 端到端回答质量 — 指标计算

读取 data/eval_results/e2e_gold.json，汇总：
- 每维度 20 条 macro 平均分（± 跨 rater 一致性的标准差）
- 每条 query 在 3 个维度的平均分
- 评分员一致性：Intraclass Correlation ICC(2,1)（双向随机，单一评分者）
  纯 numpy 手算，避免引入 pingouin 依赖。
- Cronbach's α（作为备用一致性指标）

用法:
    python -m src.eval.e2e_metrics

输出:
    data/eval_results/e2e_metrics.json
    data/eval_results/e2e_report.md
"""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_PATH = ROOT / "data" / "eval_results" / "e2e_gold.json"
METRICS_PATH = ROOT / "data" / "eval_results" / "e2e_metrics.json"
REPORT_PATH = ROOT / "data" / "eval_results" / "e2e_report.md"

DIMENSIONS = ["relevance", "completeness", "readability"]
RATERS = ["claude", "chatgpt", "gemini"]


def _variance(vals: list[float]) -> float:
    return statistics.variance(vals) if len(vals) > 1 else 0.0


def icc_2_1(matrix: list[list[float]]) -> float | None:
    """ICC(2,1) 双向随机一致性（单测量）。

    matrix[i][j] = subject i 的 rater j 打分。
    公式：ICC = (MSR - MSE) / (MSR + (k-1)*MSE + k*(MSC - MSE)/n)

    参考：Shrout & Fleiss (1979)
    """
    n = len(matrix)
    if n == 0:
        return None
    k = len(matrix[0])
    if k < 2:
        return None

    # 过滤掉含 None 的 subject
    clean = [row for row in matrix if all(v is not None for v in row)]
    if len(clean) < 2:
        return None

    n = len(clean)
    grand = sum(sum(row) for row in clean) / (n * k)
    # Between-subjects MS (MSR)
    subject_means = [sum(row) / k for row in clean]
    ssr = k * sum((m - grand) ** 2 for m in subject_means)
    msr = ssr / (n - 1)
    # Between-raters MS (MSC)
    rater_means = [sum(clean[i][j] for i in range(n)) / n for j in range(k)]
    ssc = n * sum((rm - grand) ** 2 for rm in rater_means)
    msc = ssc / (k - 1)
    # Residual MS (MSE)
    sst = sum((clean[i][j] - grand) ** 2 for i in range(n) for j in range(k))
    sse = sst - ssr - ssc
    mse = sse / ((n - 1) * (k - 1))
    if mse <= 0:
        mse = 1e-9

    denom = msr + (k - 1) * mse + k * (msc - mse) / n
    if denom == 0:
        return None
    return (msr - mse) / denom


def cronbach_alpha(matrix: list[list[float]]) -> float | None:
    """Cronbach's α 内部一致性指标。matrix[i][j] = subject i rater j."""
    clean = [row for row in matrix if all(v is not None for v in row)]
    if len(clean) < 2:
        return None
    k = len(clean[0])
    if k < 2:
        return None
    item_vars = []
    for j in range(k):
        col = [row[j] for row in clean]
        item_vars.append(_variance(col))
    totals = [sum(row) for row in clean]
    total_var = _variance(totals)
    if total_var == 0:
        return None
    return (k / (k - 1)) * (1 - sum(item_vars) / total_var)


def main() -> int:
    if not GOLD_PATH.exists():
        print(f"[error] {GOLD_PATH} not found，先跑 merge_e2e_reviews --apply", file=sys.stderr)
        return 1

    with GOLD_PATH.open("r", encoding="utf-8") as f:
        gold = json.load(f)

    n = len(gold)
    if n == 0:
        print("[error] gold 空", file=sys.stderr)
        return 1

    # 每维度 per-query mean → 再对 20 条 macro 平均
    per_dim_means: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    per_dim_stds: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    for rec in gold:
        for d in DIMENSIONS:
            m = rec["mean"].get(d)
            s = rec["std"].get(d)
            if m is not None:
                per_dim_means[d].append(m)
            if s is not None:
                per_dim_stds[d].append(s)

    macro_mean = {d: round(sum(per_dim_means[d]) / len(per_dim_means[d]), 3)
                  for d in DIMENSIONS if per_dim_means[d]}
    mean_std = {d: round(sum(per_dim_stds[d]) / len(per_dim_stds[d]), 3)
                for d in DIMENSIONS if per_dim_stds[d]}

    # 每维度构造 n × k 矩阵（subjects × raters）算 ICC / α
    icc: dict[str, float | None] = {}
    alpha: dict[str, float | None] = {}
    for d in DIMENSIONS:
        matrix = []
        for rec in gold:
            row = [rec["per_rater"][r].get(d) for r in RATERS]
            matrix.append(row)
        icc[d] = icc_2_1(matrix)
        alpha[d] = cronbach_alpha(matrix)

    def _r(v):
        return None if v is None else round(v, 3)

    metrics = {
        "total_queries": n,
        "raters": RATERS,
        "dimensions": DIMENSIONS,
        "macro_mean": macro_mean,
        "mean_cross_rater_std": mean_std,
        "icc_2_1": {d: _r(icc[d]) for d in DIMENSIONS},
        "cronbach_alpha": {d: _r(alpha[d]) for d in DIMENSIONS},
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 端到端回答质量评估报告 (§7.6)",
        "",
        f"- 查询数：**{n}** 条（从 40 条 test_queries 中挑选，覆盖 7 类别 + 多字段组合 + 硬过滤）",
        f"- 打分者：3 家 LLM 自动评估（Claude / ChatGPT / Gemini）独立打分，参考 G-Eval / MT-Bench 范式，各维度 1-5 分",
        f"- 三维定义：",
        f"  - **Relevance** 相关性 — 返回职位是否匹配查询核心约束",
        f"  - **Completeness** 完整性 — 答案是否覆盖查询涉及的所有重要字段",
        f"  - **Readability** 可读性 — 语言是否清晰、结构是否便于阅读",
        "",
        "## 三维总评",
        "",
        "| 维度 | Macro 平均 | 跨打分者 std 的平均 | ICC(2,1) | Cronbach α |",
        "|---|---|---|---|---|",
    ]
    for d in DIMENSIONS:
        mm = macro_mean.get(d)
        ms = mean_std.get(d)
        ic = icc[d]
        al = alpha[d]
        lines.append(
            f"| {d} | {mm if mm is not None else 'N/A'} | "
            f"{ms if ms is not None else 'N/A'} | "
            f"{round(ic, 3) if ic is not None else 'N/A'} | "
            f"{round(al, 3) if al is not None else 'N/A'} |"
        )

    lines.extend([
        "",
        "- ICC(2,1) / Cronbach α 解读：>0.75 良好，0.5-0.75 中等，<0.5 弱一致。",
        "",
        "## 每条 query 明细",
        "",
        "| query_id | query | relevance | completeness | readability | 平均 |",
        "|---|---|---|---|---|---|",
    ])
    for rec in gold:
        qid = rec["query_id"]
        q = (rec["query"][:40] + "…") if len(rec["query"]) > 40 else rec["query"]
        m = rec["mean"]
        vals = [m[d] for d in DIMENSIONS if m.get(d) is not None]
        avg = round(sum(vals) / len(vals), 2) if vals else None
        lines.append(
            f"| {qid} | {q} | "
            f"{m.get('relevance', 'N/A')} | "
            f"{m.get('completeness', 'N/A')} | "
            f"{m.get('readability', 'N/A')} | "
            f"{avg if avg is not None else 'N/A'} |"
        )

    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Macro 平均：")
    for d in DIMENSIONS:
        print(f"  {d:<14} mean={macro_mean.get(d, 'N/A'):<6} std_avg={mean_std.get(d, 'N/A'):<6} "
              f"ICC={icc[d] if icc[d] is None else round(icc[d], 3)}")
    print(f"已写入:")
    print(f"  - {METRICS_PATH}")
    print(f"  - {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
