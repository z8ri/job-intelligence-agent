"""
Section 7.3 classification accuracy: metric computation.

Reads data/eval_results/classification_gold.json, compares the classifier's
predictions (predicted_category) against gold (gold_category), and computes
accuracy, per-class P/R/F1 and a confusion matrix.

Usage:
    python -m src.eval.class_metrics

Outputs:
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
    """Render the confusion matrix as a markdown table."""
    header = "| pred \\ gold | " + " | ".join(labels) + " |"
    sep = "|" + "---|" * (len(labels) + 1)
    rows = [header, sep]
    for i, row_label in enumerate(labels):
        cells = [row_label] + [str(cm[i][j]) for j in range(len(labels))]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def main() -> int:
    if not GOLD_PATH.exists():
        print(f"[error] {GOLD_PATH} not found; run merge_class_reviews --apply first", file=sys.stderr)
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
    # We display the transpose (rows=pred, cols=gold), which reads more naturally:
    # "of the items predicted as X, how many were actually Y"
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
        "# Job Classification Accuracy Report (Section 7.3)",
        "",
        f"- Test set size: **{total}** items (stratified sample across 7 classes from 2013 predictions over the full DB, excluding the 120 training items)",
        f"- Gold source: independent classification by Claude / ChatGPT / Gemini + majority vote",
        f"- Unanimous / majority / human-resolved: {verdict_counts.get('unanimous', 0)} / {verdict_counts.get('majority', 0)} / {verdict_counts.get('human_resolved', 0)}",
        "",
        f"## Overall",
        "",
        f"- **Accuracy: {accuracy:.3f}** ({correct}/{total})",
        f"- Macro  P/R/F1: {metrics['macro_avg']['precision']:.3f} / {metrics['macro_avg']['recall']:.3f} / {metrics['macro_avg']['f1']:.3f}",
        f"- Weighted P/R/F1: {metrics['weighted_avg']['precision']:.3f} / {metrics['weighted_avg']['recall']:.3f} / {metrics['weighted_avg']['f1']:.3f}",
        "",
        "## Per-class metrics",
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
        "## Confusion matrix",
        "",
        "Rows = classifier prediction, columns = gold category. The diagonal is the count of correct predictions.",
        "",
        build_confusion_md(cm_pred_true.tolist(), CATEGORIES),
        "",
    ])

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Accuracy: {accuracy:.3f} ({correct}/{total})")
    print(f"Macro F1: {metrics['macro_avg']['f1']:.3f}")
    print(f"Written:")
    print(f"  - {METRICS_PATH}")
    print(f"  - {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
