# Agent evaluation report

## Frozen inputs

- snapshots: 2613
- snapshot_digest: 3d5ecec1e6187c27
- queries: 16
- query_set_digest: 68c3f15462f75407
- llm_model: gpt-4o-mini
- judge_prompt_version: 1
- annotator_version: 1
- embedding_model: text-embedding-3-small
- reranker: CrossEncoderScorer:BAAI/bge-reranker-base
- k: 5
- max_candidates: 20
- live_llm_spend_usd_estimated: 0.1772

Labels are silver (model-annotated, different prompt from the system) unless a row says human. 'valid' = work-relevant and every hard condition confirmed satisfied, counted in the top 5; unstated is not confirmed. Token/cost figures are estimates (chars/3), cold cache per system.

## dev

| system | queries | valid@5 | wrong accept@5 | unlabeled@5 | nDCG@5 | LLM calls/q | est tokens/q | est $/q |
|---|---|---|---|---|---|---|---|---|
| retrieval_raw | 8 | 1.12 | 3.50 | 0.00 | 0.376 | 0.0 | 0 | 0.00000 |
| retrieval | 8 | 0.62 | 4.00 | 0.00 | 0.224 | 0.0 | 0 | 0.00000 |
| rerank | 8 | 0.75 | 3.62 | 0.00 | 0.220 | 0.0 | 0 | 0.00000 |
| verify_fixed | 8 | 0.38 | 0.50 | 0.00 | 0.216 | 4.8 | 7531 | 0.00160 |
| verify_ondemand | 8 | 0.75 | 1.50 | 0.00 | 0.277 | 15.8 | 27472 | 0.00560 |
| verify_full | 8 | 0.75 | 1.50 | 0.00 | 0.277 | 18.0 | 31631 | 0.00640 |

Paired differences in valid@5 (a - b), 95% bootstrap interval over queries:

| a | b | what | n | mean diff | 95% CI | win/loss/tie | calls diff |
|---|---|---|---|---|---|---|---|
| retrieval | retrieval_raw | input organisation: role/skill text vs raw request | 8 | -0.50 | [-1.25, +0.00] | 0/2/6 | +0.0 |
| rerank | retrieval | cross-encoder rerank vs retrieval order | 8 | +0.12 | [-0.25, +0.50] | 2/1/5 | +0.0 |
| verify_ondemand | verify_fixed | on-demand verification (backfill) vs fixed top-k | 8 | +0.38 | [+0.00, +0.88] | 2/0/6 | +11.0 |
| verify_ondemand | verify_full | on-demand verification vs verify-everything | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | -2.2 |

## holdout

| system | queries | valid@5 | wrong accept@5 | unlabeled@5 | nDCG@5 | LLM calls/q | est tokens/q | est $/q |
|---|---|---|---|---|---|---|---|---|
| retrieval_raw | 8 | 1.25 | 3.50 | 0.00 | 0.372 | 0.0 | 0 | 0.00000 |
| retrieval | 8 | 1.00 | 3.75 | 0.00 | 0.244 | 0.0 | 0 | 0.00000 |
| rerank | 8 | 1.25 | 3.50 | 0.00 | 0.444 | 0.0 | 0 | 0.00000 |
| verify_fixed | 8 | 1.12 | 1.00 | 0.00 | 0.319 | 5.0 | 9772 | 0.00190 |
| verify_ondemand | 8 | 1.25 | 2.00 | 0.00 | 0.336 | 14.1 | 29070 | 0.00560 |
| verify_full | 8 | 1.25 | 2.00 | 0.00 | 0.336 | 19.4 | 37734 | 0.00720 |

Paired differences in valid@5 (a - b), 95% bootstrap interval over queries:

| a | b | what | n | mean diff | 95% CI | win/loss/tie | calls diff |
|---|---|---|---|---|---|---|---|
| retrieval | retrieval_raw | input organisation: role/skill text vs raw request | 8 | -0.25 | [-0.62, +0.00] | 0/2/6 | +0.0 |
| rerank | retrieval | cross-encoder rerank vs retrieval order | 8 | +0.25 | [+0.00, +0.62] | 2/0/6 | +0.0 |
| verify_ondemand | verify_fixed | on-demand verification (backfill) vs fixed top-k | 8 | +0.12 | [+0.00, +0.38] | 1/0/7 | +9.1 |
| verify_ondemand | verify_full | on-demand verification vs verify-everything | 8 | +0.00 | [+0.00, +0.00] | 0/0/8 | -5.2 |

## Regressions kept for inspection

- d01 (dev): retrieval valid 0 < retrieval_raw valid 1
- d07 (dev): retrieval valid 0 < retrieval_raw valid 3
- h01 (holdout): retrieval valid 1 < retrieval_raw valid 2
- h06 (holdout): retrieval valid 1 < retrieval_raw valid 2
- d03 (dev): rerank valid 0 < retrieval valid 1

Small query counts: differences are indicative, not significant unless the interval excludes 0.
