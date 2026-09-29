# Agent evaluation report

## Frozen inputs

- snapshots: 2613
- snapshot_digest: 3d5ecec1e6187c27
- queries: 16
- query_set_digest: 68c3f15462f75407
- llm_model: gpt-4o-mini
- judge_prompt_version: 2
- annotator_version: 1
- embedding_model: text-embedding-3-small
- reranker: CrossEncoderScorer:BAAI/bge-reranker-base
- k: 5
- max_candidates: 20
- live_llm_spend_usd_estimated: 0.3496

Labels are silver (model-annotated, different prompt from the system) unless a row says human. 'valid' = work-relevant and every hard condition confirmed satisfied, counted in the top 5; unstated is not confirmed. Token/cost figures are estimates (chars/3), cold cache per system.

## dev

| system | queries | valid@5 | wrong accept@5 | unlabeled@5 | nDCG@5 | LLM calls/q | est tokens/q | est $/q |
|---|---|---|---|---|---|---|---|---|
| retrieval_raw | 8 | 1.12 | 3.38 | 0.00 | 0.376 | 0.0 | 0 | 0.00000 |
| retrieval | 8 | 0.62 | 3.88 | 0.00 | 0.224 | 0.0 | 0 | 0.00000 |
| rerank | 8 | 0.75 | 3.62 | 0.00 | 0.220 | 0.0 | 0 | 0.00000 |
| verify_fixed | 8 | 0.50 | 0.25 | 0.00 | 0.243 | 4.6 | 7856 | 0.00160 |
| verify_ondemand | 8 | 1.00 | 0.75 | 0.00 | 0.443 | 15.1 | 28594 | 0.00560 |
| verify_planned | 8 | 1.00 | 0.75 | 0.00 | 0.443 | 15.0 | 28376 | 0.00560 |
| verify_full | 8 | 1.00 | 0.75 | 0.00 | 0.443 | 17.9 | 33355 | 0.00660 |
| verify_full_confirmed_first | 8 | 1.00 | 0.75 | 0.00 | 0.453 | 17.9 | 33355 | 0.00660 |

Paired differences in valid@5 (a - b), 95% bootstrap interval over queries:

| a | b | what | n | mean diff | 95% CI | win/loss/tie | calls diff |
|---|---|---|---|---|---|---|---|
| retrieval | retrieval_raw | input organisation: role/skill text vs raw request | 8 | -0.50 | [-1.25, +0.00] | 0/2/6 | +0.0 |
| rerank | retrieval | cross-encoder rerank vs retrieval order | 8 | +0.12 | [-0.25, +0.50] | 2/1/5 | +0.0 |
| verify_ondemand | verify_fixed | on-demand verification (backfill) vs fixed top-k | 8 | +0.50 | [+0.12, +0.88] | 4/0/4 | +10.5 |
| verify_ondemand | verify_full | on-demand verification vs verify-everything | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | -2.8 |
| verify_planned | verify_ondemand | planned order (hint-contradicted candidates last) vs plain rank order, both on-demand | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | -0.1 |
| verify_full_confirmed_first | verify_full | confirmed-hard jobs ranked before needs-confirmation jobs vs plain order | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | +0.0 |

## holdout

| system | queries | valid@5 | wrong accept@5 | unlabeled@5 | nDCG@5 | LLM calls/q | est tokens/q | est $/q |
|---|---|---|---|---|---|---|---|---|
| retrieval_raw | 8 | 1.38 | 3.38 | 0.00 | 0.431 | 0.0 | 0 | 0.00000 |
| retrieval | 8 | 1.25 | 3.75 | 0.00 | 0.292 | 0.0 | 0 | 0.00000 |
| rerank | 8 | 1.50 | 3.38 | 0.00 | 0.504 | 0.0 | 0 | 0.00000 |
| verify_fixed | 8 | 1.38 | 0.50 | 0.00 | 0.503 | 5.0 | 10202 | 0.00190 |
| verify_ondemand | 8 | 1.62 | 1.88 | 0.00 | 0.537 | 14.8 | 30382 | 0.00580 |
| verify_planned | 8 | 1.62 | 1.88 | 0.00 | 0.537 | 14.4 | 29651 | 0.00560 |
| verify_full | 8 | 1.62 | 1.88 | 0.00 | 0.537 | 19.4 | 39472 | 0.00740 |
| verify_full_confirmed_first | 8 | 1.62 | 1.88 | 0.00 | 0.537 | 19.4 | 39472 | 0.00740 |

Paired differences in valid@5 (a - b), 95% bootstrap interval over queries:

| a | b | what | n | mean diff | 95% CI | win/loss/tie | calls diff |
|---|---|---|---|---|---|---|---|
| retrieval | retrieval_raw | input organisation: role/skill text vs raw request | 8 | -0.12 | [-0.50, +0.25] | 1/2/5 | +0.0 |
| rerank | retrieval | cross-encoder rerank vs retrieval order | 8 | +0.25 | [+0.00, +0.62] | 2/0/6 | +0.0 |
| verify_ondemand | verify_fixed | on-demand verification (backfill) vs fixed top-k | 8 | +0.25 | [+0.00, +0.75] | 1/0/7 | +9.8 |
| verify_ondemand | verify_full | on-demand verification vs verify-everything | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | -4.6 |
| verify_planned | verify_ondemand | planned order (hint-contradicted candidates last) vs plain rank order, both on-demand | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | -0.4 |
| verify_full_confirmed_first | verify_full | confirmed-hard jobs ranked before needs-confirmation jobs vs plain order | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | +0.0 |

## Regressions kept for inspection

- d01 (dev): retrieval valid 0 < retrieval_raw valid 1
- d07 (dev): retrieval valid 0 < retrieval_raw valid 3
- h01 (holdout): retrieval valid 1 < retrieval_raw valid 2
- h06 (holdout): retrieval valid 1 < retrieval_raw valid 2
- d03 (dev): rerank valid 0 < retrieval valid 1

Small query counts: differences are indicative, not significant unless the interval excludes 0.
