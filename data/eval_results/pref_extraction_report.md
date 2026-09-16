# Preference Extraction Accuracy Report (§7.2)

- Test queries: **40** (the full `data/test_queries.json`).
- Gold labels: independent extractions from Claude / ChatGPT / Gemini + per-field majority vote.
- System under test: gpt-4o-mini (`src/llm/query_understanding.py`).

## Per-field accuracy

| Field | Match rule | Accuracy |
|---|---|---|
| target_salary | error ≤ $10,000 | 0.950 |
| preferred_location | lowercase string equality | 0.975 |
| remote_preference | exact equality | 0.975 |
| preferred_category | exact equality | 0.875 |
| desired_tags | Jaccard ≥ 0.6 | 0.900 |
| description_keywords | Jaccard ≥ 0.6 | 0.775 |
| weight_adjustments | dict equality | 0.775 |

- **Macro-field accuracy: 0.889**
- All fields simultaneously correct: 17/40 (0.425)

## Failure cases (first 10)

- **q01**: `Remote Python backend jobs above 150k`
  - `description_keywords` — gold: `["backend"]` vs sys: `["python", "backend"]`
- **q02**: `Jobs paying over 200k in machine learning`
  - `preferred_category` — gold: `"data"` vs sys: `null`
  - `desired_tags` — gold: `["machine learning"]` vs sys: `null`
- **q03**: `Entry level software engineering positions in the 70-90k range`
  - `target_salary` — gold: `80000` vs sys: `null`
  - `weight_adjustments` — gold: `{}` vs sys: `{"salary": "medium"}`
- **q05**: `Data science positions around 130k to 160k`
  - `target_salary` — gold: `145000` vs sys: `null`
  - `weight_adjustments` — gold: `{}` vs sys: `{"salary": "medium"}`
- **q08**: `Tech jobs in New York City area`
  - `description_keywords` — gold: `["tech"]` vs sys: `null`
- **q10**: `Jobs in Austin Texas for full stack developers`
  - `preferred_location` — gold: `"austin, texas"` vs sys: `"Austin"`
- **q11**: `Fully remote senior engineering roles`
  - `description_keywords` — gold: `["engineering", "senior"]` vs sys: `["senior engineering"]`
- **q17**: `Python and AWS cloud engineer positions`
  - `preferred_category` — gold: `"devops"` vs sys: `null`
- **q18**: `Golang microservices developer`
  - `preferred_category` — gold: `"backend"` vs sys: `null`
  - `description_keywords` — gold: `["microservices developer"]` vs sys: `["Golang", "microservices", "developer"]`
- **q19**: `Rust systems programming jobs`
  - `preferred_category` — gold: `"backend"` vs sys: `null`
