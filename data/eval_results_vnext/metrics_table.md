| Config | P@5 | P@10 | nDCG@5 | nDCG@10 | Description |
|--------|-----|------|--------|---------|-------------|
| tfidf_only | 0.355 | 0.392 | 0.386 | 0.566 | TF-IDF description score only, no structured fields |
| bm25_only | 0.375 | 0.380 | 0.392 | 0.567 | BM25 description score only, no structured fields |
| hybrid_text | 0.335 | 0.398 | 0.352 | 0.564 | TF-IDF + BM25 average (description only), no structured fields |
| dense_only | 0.410 | 0.407 | 0.438 | 0.625 | Dense (OpenAI embedding) description score only, no structured fields |
| hybrid_rrf | 0.475 | 0.470 | 0.500 | 0.672 | BM25 + Dense fused via Reciprocal Rank Fusion (description only), no structured fields |
| hybrid_rrf_reranked | 0.620 | 0.552 | 0.596 | 0.743 | hybrid_rrf + LLM reranker on top-50 (description only), no structured fields |
| structured_only | 0.325 | 0.282 | 0.416 | 0.507 | Structured fields only (salary, location, remote, tags), no description |
| all_equal_weights | 0.535 | 0.538 | 0.539 | 0.700 | All fields with equal 1/6 weight |
| all_default_weights | 0.545 | 0.548 | 0.545 | 0.708 | All fields with predefined default weights |
| all_adaptive_weights | 0.545 | 0.545 | 0.552 | 0.710 | All fields with LLM query-adaptive weights |
| hard_filter_baseline | 0.435 | 0.458 | 0.445 | 0.592 | SQL WHERE hard filters instead of soft scoring |
| no_expansion | 0.540 | 0.537 | 0.513 | 0.696 | All fields, query expansion disabled |
| with_expansion | 0.545 | 0.545 | 0.552 | 0.710 | All fields, query expansion enabled |
| no_category | 0.485 | 0.520 | 0.482 | 0.660 | All fields except category in scoring |
| with_category | 0.545 | 0.545 | 0.552 | 0.710 | All fields including category in scoring |
