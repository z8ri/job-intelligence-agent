# End-to-End Answer Quality Evaluation Report (§7.6)

- Number of queries: **20** (sampled from 40 `test_queries`, covering all 7 categories + multi-field combinations + hard filters).
- Raters: 3 LLMs as automatic evaluators (Claude / ChatGPT / Gemini), independently scored, following the G-Eval / MT-Bench paradigm; 1–5 integer scale per dimension.
- Three dimensions:
  - **Relevance** — do the returned jobs match the core query constraints?
  - **Completeness** — does the answer cover every important field mentioned in the query?
  - **Readability** — is the language clear and the structure easy to scan?

## Overall scores

| Dimension | Macro mean | Mean cross-rater std | ICC(2,1) | Cronbach α |
|---|---|---|---|---|
| relevance | 3.167 | 0.165 | 0.878 | 0.959 |
| completeness | 3.6 | 0.3 | 0.356 | 0.664 |
| readability | 4.216 | 0.512 | 0.133 | 0.662 |

- ICC(2,1) / Cronbach α reading: > 0.75 good, 0.5–0.75 moderate, < 0.5 weak agreement.

## Per-query detail

| query_id | query | relevance | completeness | readability | mean |
|---|---|---|---|---|---|
| q01 | Remote Python backend jobs above 150k | 4.0 | 4.0 | 4.333 | 4.11 |
| q05 | Data science positions around 130k to 16… | 2.333 | 3.667 | 4.333 | 3.44 |
| q07 | Positions near Boston for backend develo… | 2.0 | 3.667 | 4.333 | 3.33 |
| q11 | Fully remote senior engineering roles | 4.0 | 3.667 | 4.0 | 3.89 |
| q14 | 100% remote data engineering jobs | 4.0 | 4.0 | 3.667 | 3.89 |
| q15 | React and TypeScript frontend developer … | 4.0 | 4.0 | 4.667 | 4.22 |
| q16 | Kubernetes and Terraform DevOps engineer | 2.667 | 2.667 | 4.333 | 3.22 |
| q20 | Mobile development jobs with Flutter or … | 3.0 | 3.333 | 4.333 | 3.56 |
| q22 | Engineering manager or tech lead opening… | 4.333 | 4.0 | 3.667 | 4.0 |
| q25 | Site reliability engineer SRE jobs | 5.0 | 4.333 | 4.333 | 4.56 |
| q26 | Remote ML jobs in New York above 130k | 3.0 | 3.0 | 4.333 | 3.44 |
| q27 | Backend Go developer, hybrid, 160k or mo… | 3.333 | 4.0 | 4.333 | 3.89 |
| q28 | Full stack JavaScript developer in San F… | 3.667 | 3.667 | 4.333 | 3.89 |
| q29 | Senior data engineer with Spark and Kafk… | 2.0 | 3.667 | 4.333 | 3.33 |
| q30 | React frontend roles in Chicago or nearb… | 2.0 | 3.333 | 4.333 | 3.22 |
| q31 | DevOps with AWS and Docker in Austin, hy… | 2.0 | 4.0 | 4.333 | 3.44 |
| q32 | Remote Python or Java backend, good sala… | 4.0 | 3.333 | 4.333 | 3.89 |
| q33 | Management positions in Denver or Boulde… | 2.0 | 3.667 | 4.333 | 3.33 |
| q34 | Companies with good culture for junior d… | 3.333 | 3.0 | 3.333 | 3.22 |
| q35 | Fast-paced startup environment with equi… | 2.667 | 3.0 | 4.333 | 3.33 |
