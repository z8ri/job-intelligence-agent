# Job Classification Accuracy Report (§7.3)

- Test set size: **63** (stratified sample of 7 classes drawn from 2,013 full-corpus predictions, excluding the 120 training-set entries).
- Gold labels: independent classifications from Claude / ChatGPT / Gemini + majority vote.
- Unanimous / majority / human-resolved: 53 / 10 / 0.

## Overall

- **Accuracy: 0.476** (30/63)
- Macro  P/R/F1: 0.569 / 0.493 / 0.490
- Weighted P/R/F1: 0.550 / 0.476 / 0.475

## Per-class metrics

| category | precision | recall | F1 | support |
|---|---|---|---|---|
| backend | 0.500 | 0.300 | 0.375 | 20 |
| frontend | 0.600 | 0.500 | 0.545 | 6 |
| data | 0.667 | 0.400 | 0.500 | 10 |
| devops | 0.286 | 0.667 | 0.400 | 6 |
| fullstack | 0.429 | 0.750 | 0.545 | 12 |
| mobile | 0.500 | 0.333 | 0.400 | 3 |
| management | 1.000 | 0.500 | 0.667 | 6 |

## Confusion matrix

Rows = predicted class; columns = gold class. The diagonal is the count of correct predictions.

| pred \ gold | backend | frontend | data | devops | fullstack | mobile | management |
|---|---|---|---|---|---|---|---|
| backend | 6 | 0 | 1 | 1 | 1 | 1 | 2 |
| frontend | 0 | 3 | 0 | 0 | 1 | 1 | 0 |
| data | 1 | 0 | 4 | 0 | 1 | 0 | 0 |
| devops | 9 | 0 | 1 | 4 | 0 | 0 | 0 |
| fullstack | 4 | 3 | 4 | 1 | 9 | 0 | 0 |
| mobile | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| management | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
