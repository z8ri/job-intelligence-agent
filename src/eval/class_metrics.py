"""
§7.3 分类准确率 — 指标计算

读取 data/eval_results/classification_gold.json，
对比分类器预测值（predicted_category）和 gold（gold_category），
计算 accuracy / per-class P-R-F1 / 混淆矩阵。

用法:
    python -m src.eval.class_metrics

输出:
    data/eval_results/classification_metrics.json
    data/eval_results/classification_report.md
"""

import json
import sys
from collections import Counter
from pathlib import Path

from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_PATH = ROOT / "data" / "eval_results" / "classification_gold.json"
METRICS_PATH = ROOT / "data" / "eval_results" / "classification_metrics.json"
REPORT_PATH = ROOT / "data" / "eval_results" / "classification_report.md"

CATEGORIES = ["backend", "frontend", "data", "devops", "fullstack", "mobile", "management"]


def build_confusion_md(cm, labels: list[str]) -> str:
    """生成 markdown 混淆矩阵表格。"""
    header = "| pred \\ gold | " + " | ".join(labels) + " |"
    sep = "|" + "---|" * (len(labels) + 1)
    rows = [header, sep]
    for i, row_label in enumerate(labels):
        cells = [row_label] + [str(cm[i][j]) for j in range(len(labels))]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def main() -> int:
    if not GOLD_PATH.exists():
        print(f"[error] {GOLD_PATH} not found，先跑 merge_class_reviews --apply", file=sys.stderr)
        return 1

    with GOLD_PATH.open("r", encoding="utf-8") as f:
        gold = json.load(f)

    y_pred = [g["predicted_category"] for g in gold]
    y_true = [g["gold_category"] for g in gold]

    total = len(gold)
    correct = sum(1 for p, t in zip(y_pred, y_true) if p == t)
    accuracy = correct / total if total else 0.0

    verdict_counts = Counter(g["verdict"] for g in gold)

    report_dict = classification_report(
        y_true,
        y_pred,
        labels=CATEGORIES,
        target_names=CATEGORIES,
        zero_division=0,
        output_dict=True,
    )

    # sklearn confusion_matrix: rows = true, cols = pred
    # 我们展示时转置为 rows=pred, cols=gold（贴合阅读习惯："预测为X的里有多少真实为Y"）
    cm_true_pred = confusion_matrix(y_true, y_pred, labels=CATEGORIES)
    cm_pred_true = cm_true_pred.T  # transpose

    metrics = {
        "total": total,
        "accuracy": accuracy,
        "verdict_counts": dict(verdict_counts),
        "per_class": {
            cat: {
                "precision": report_dict[cat]["precision"],
                "recall": report_dict[cat]["recall"],
                "f1": report_dict[cat]["f1-score"],
                "support": int(report_dict[cat]["support"]),
            }
            for cat in CATEGORIES
        },
        "macro_avg": {
            "precision": report_dict["macro avg"]["precision"],
            "recall": report_dict["macro avg"]["recall"],
            "f1": report_dict["macro avg"]["f1-score"],
        },
        "weighted_avg": {
            "precision": report_dict["weighted avg"]["precision"],
            "recall": report_dict["weighted avg"]["recall"],
            "f1": report_dict["weighted avg"]["f1-score"],
        },
    }

    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 职位分类准确率评估报告 (§7.3)",
        "",
        f"- 测试集规模：**{total}** 条（从全库 2013 条预测中按 7 类分层抽样，排除 120 条训练集）",
        f"- Gold 来源：Claude / ChatGPT / Gemini 三家独立分类 + 多数投票",
        f"- 一致 / 多数 / 人工裁决：{verdict_counts.get('unanimous', 0)} / {verdict_counts.get('majority', 0)} / {verdict_counts.get('human_resolved', 0)}",
        "",
        f"## 总体",
        "",
        f"- **Accuracy: {accuracy:.3f}** ({correct}/{total})",
        f"- Macro  P/R/F1: {metrics['macro_avg']['precision']:.3f} / {metrics['macro_avg']['recall']:.3f} / {metrics['macro_avg']['f1']:.3f}",
        f"- Weighted P/R/F1: {metrics['weighted_avg']['precision']:.3f} / {metrics['weighted_avg']['recall']:.3f} / {metrics['weighted_avg']['f1']:.3f}",
        "",
        "## 每类指标",
        "",
        "| category | precision | recall | F1 | support |",
        "|---|---|---|---|---|",
    ]
    for cat in CATEGORIES:
        m = metrics["per_class"][cat]
        lines.append(
            f"| {cat} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['support']} |"
        )

    lines.extend([
        "",
        "## 混淆矩阵",
        "",
        "行 = 分类器预测类别，列 = gold 类别。对角线即正确预测数。",
        "",
        build_confusion_md(cm_pred_true.tolist(), CATEGORIES),
        "",
    ])

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Accuracy: {accuracy:.3f} ({correct}/{total})")
    print(f"Macro F1: {metrics['macro_avg']['f1']:.3f}")
    print(f"已写入:")
    print(f"  - {METRICS_PATH}")
    print(f"  - {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
