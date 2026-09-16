| Config | P@5 | P@10 | nDCG@5 | nDCG@10 | Description |
|--------|-----|------|--------|---------|-------------|
| tfidf_only | 0.350 | 0.375 | 0.378 | 0.551 | TF-IDF description score only, no structured fields |
| bm25_only | 0.375 | 0.380 | 0.392 | 0.567 | BM25 description score only, no structured fields |
| hybrid_text | 0.330 | 0.400 | 0.339 | 0.559 | TF-IDF + BM25 average (description only), no structured fields |
| structured_only | 0.305 | 0.275 | 0.396 | 0.498 | Structured fields only (salary, location, remote, tags), no description |
| all_equal_weights | 0.535 | 0.543 | 0.528 | 0.698 | All fields with equal 1/6 weight |
| all_default_weights | 0.540 | 0.543 | 0.536 | 0.700 | All fields with predefined default weights |
| all_adaptive_weights | 0.545 | 0.543 | 0.544 | 0.701 | All fields with LLM query-adaptive weights |
| hard_filter_baseline | 0.430 | 0.447 | 0.441 | 0.599 | SQL WHERE hard filters instead of soft scoring |
| no_expansion | 0.545 | 0.538 | 0.516 | 0.696 | All fields, query expansion disabled |
| with_expansion | 0.545 | 0.543 | 0.544 | 0.701 | All fields, query expansion enabled |
| no_category | 0.445 | 0.510 | 0.443 | 0.634 | All fields except category in scoring |
| with_category | 0.545 | 0.543 | 0.544 | 0.701 | All fields including category in scoring |
