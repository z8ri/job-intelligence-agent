"""§7.5 score function visualizations — generate 4 PNGs to data/eval_results/figures/.

Plots:
  1. salary_score.png        — asymmetric Gaussian decay (target=$100k)
  2. location_score.png      — 6-tier hierarchical bar chart
  3. remote_matrix.png       — 4×5 preference compatibility heatmap
  4. jaccard_comparison.png  — modified Jaccard (ours) vs standard Jaccard

Usage:
    python -m src.eval.score_function_plots
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.eval import PROJECT_ROOT
from src.scoring.engine import ScoringEngine

FIGURES_DIR = PROJECT_ROOT / "data" / "eval_results" / "figures"


# ---------- Fig 1: salary asymmetric Gaussian ----------

def plot_salary(engine: ScoringEngine, out_path: Path) -> None:
    target = 100_000
    salaries = np.linspace(50_000, 200_000, 1000)
    scores = [
        engine.score_salary({"salary_min": int(s), "salary_max": int(s)}, target)
        for s in salaries
    ]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    ax.plot(salaries / 1000, scores, color="#1f77b4", linewidth=2)

    ax.axvspan(50, 100, alpha=0.10, color="red", label=r"$\sigma_{\mathrm{low}}=20{,}000$ (harsher)")
    ax.axvspan(100, 200, alpha=0.10, color="green", label=r"$\sigma_{\mathrm{high}}=50{,}000$ (lenient)")

    ax.axvline(target / 1000, color="black", linestyle="--", linewidth=1)
    ax.annotate("target = $100k\nscore = 1.0",
                xy=(100, 1.0), xytext=(110, 0.92),
                fontsize=9,
                arrowprops=dict(arrowstyle="->", color="black", lw=0.8))

    half_low = target - np.sqrt(np.log(2)) * 20_000
    half_high = target + np.sqrt(np.log(2)) * 50_000
    ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.8)
    ax.scatter([half_low / 1000, half_high / 1000], [0.5, 0.5], color="black", zorder=5, s=20)
    ax.annotate(f"~${half_low/1000:.1f}k", xy=(half_low / 1000, 0.5),
                xytext=(half_low / 1000 - 12, 0.55), fontsize=8)
    ax.annotate(f"~${half_high/1000:.1f}k", xy=(half_high / 1000, 0.5),
                xytext=(half_high / 1000 + 2, 0.55), fontsize=8)

    ax.set_xlabel("Effective salary (USD, thousands)")
    ax.set_ylabel("Score")
    ax.set_title("Salary asymmetric Gaussian decay (target = $100,000)")
    ax.set_xlim(50, 200)
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------- Fig 2: location hierarchical bar chart ----------

def plot_location(out_path: Path) -> None:
    tiers = [
        ("Exact match", 1.0),
        ("Remote (any)", 0.9),
        ("Same metro", 0.8),
        ("Metro + state", 0.5),
        ("Unknown", 0.3),
        ("Other", 0.1),
    ]
    labels = [t[0] for t in tiers]
    values = [t[1] for t in tiers]

    cmap = plt.get_cmap("RdYlGn")
    colors = [cmap(v) for v in values]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    bars = ax.bar(labels, values, color=colors, edgecolor="black", linewidth=0.6)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02,
                f"{v:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xlabel("Tier")
    ax.set_ylabel("Score")
    ax.set_title("Location score by tier")
    ax.set_ylim(0, 1.15)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------- Fig 3: remote 4×5 heatmap ----------

def plot_remote(engine: ScoringEngine, out_path: Path) -> None:
    pref_labels = ["remote", "hybrid", "onsite", "remote_or_onsite"]
    job_labels = ["remote", "hybrid", "onsite", "unknown", "remote_or_onsite"]

    matrix = np.array([
        [engine.score_remote(j, p) for j in job_labels]
        for p in pref_labels
    ])

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    im = ax.imshow(matrix, cmap="YlGn", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(job_labels)))
    ax.set_xticklabels(job_labels, rotation=20, ha="right")
    ax.set_yticks(range(len(pref_labels)))
    ax.set_yticklabels(pref_labels)

    for i in range(len(pref_labels)):
        for j in range(len(job_labels)):
            v = matrix[i, j]
            color = "white" if v > 0.55 else "black"
            ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                    color=color, fontsize=10, fontweight="bold")

    ax.set_xlabel("Job remote type")
    ax.set_ylabel("User preference")
    ax.set_title("Remote preference compatibility matrix (rows = pref, cols = job)")
    fig.colorbar(im, ax=ax, label="Score")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


# ---------- Fig 4: modified vs standard Jaccard ----------

def plot_jaccard_comparison(out_path: Path) -> None:
    job_size = 10
    desired_sizes = np.arange(1, 11)        # 1..10
    hits_range = np.arange(0, 11)           # 0..10

    modified = np.full((len(hits_range), len(desired_sizes)), np.nan)
    standard = np.full((len(hits_range), len(desired_sizes)), np.nan)

    for i, hits in enumerate(hits_range):
        for j, d in enumerate(desired_sizes):
            if hits > d or hits > job_size:
                continue
            modified[i, j] = hits / d
            union = d + job_size - hits
            standard[i, j] = hits / union if union > 0 else 0.0

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=150)
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad(color="lightgray")

    for ax, data, title in [
        (axes[0], modified, "Modified Jaccard (ours): hits / |desired|"),
        (axes[1], standard, "Standard Jaccard: hits / |desired ∪ job|"),
    ]:
        masked = np.ma.masked_invalid(data)
        im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=1, origin="lower", aspect="auto")
        ax.set_xticks(range(len(desired_sizes)))
        ax.set_xticklabels(desired_sizes)
        ax.set_yticks(range(len(hits_range)))
        ax.set_yticklabels(hits_range)
        ax.set_xlabel("|desired_tags|")
        ax.set_ylabel("hits count")
        ax.set_title(title, fontsize=11)
        for i in range(masked.shape[0]):
            for j in range(masked.shape[1]):
                if np.ma.is_masked(masked[i, j]):
                    continue
                v = masked[i, j]
                color = "white" if v > 0.55 else "black"
                ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                        color=color, fontsize=7)

    fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02, label="Score")
    fig.suptitle("Modified Jaccard (ours, left) vs Standard Jaccard (right)  |  job_tags fixed at 10",
                 fontsize=12, y=1.02)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# ---------- entry ----------

def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    engine = ScoringEngine()

    targets = [
        ("salary_score.png", lambda p: plot_salary(engine, p)),
        ("location_score.png", lambda p: plot_location(p)),
        ("remote_matrix.png", lambda p: plot_remote(engine, p)),
        ("jaccard_comparison.png", lambda p: plot_jaccard_comparison(p)),
    ]
    for name, fn in targets:
        out = FIGURES_DIR / name
        fn(out)
        print(f"[ok] {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
