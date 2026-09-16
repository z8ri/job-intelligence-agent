# Scoring Function Validation Report (§7.5)

- Implementation: 4 atomic scoring functions in `src/scoring/engine.py` (salary / location / tags / remote).
- Tests: `tests/test_scoring.py` — 47 cases, all pass, 0.17s.
- Visualizations: `src/eval/score_function_plots.py` — 4 PNGs written to `data/eval_results/figures/`.

## Unit tests

| Function | Cases | Status |
|---|---|---|
| score_salary | 8 | 8/8 pass |
| score_location | 10 | 10/10 pass |
| score_tags | 7 | 7/7 pass |
| score_remote | 22 | 22/22 pass |
| **Total** | **47** | **47/47 pass** |

Tolerance 0.01. All numerical cases derive expected scores directly from formulas such as `math.exp(...)`; no hard-coded "expected" numbers.

How to run:

```
pytest tests/test_scoring.py -v
```

## Visualizations (4 figures)

All have English titles / axes; written to `data/eval_results/figures/`:

1. `salary_score.png` — salary asymmetric Gaussian decay curve (target = $100k).
2. `location_score.png` — location tiered-proximity 6-bucket bar chart.
3. `remote_matrix.png` — remote preference 4×5 compatibility matrix heatmap.
4. `jaccard_comparison.png` — modified Jaccard vs. standard Jaccard dual heatmap (motivation: "why we changed the formula").

How to run:

```
python -m src.eval.score_function_plots
```

Full interpretation and design rationale are in §6.5 of the report (scoring-function validation).
