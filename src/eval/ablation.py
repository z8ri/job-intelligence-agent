"""
Ablation experiment configs. The configurations here are used by
`src.eval.pool_eval` as the canonical runner — it reads ABLATION_CONFIGS and
materializes each config by rewriting preferences (see apply_config_to_prefs).

`run_single_config` / `run_all_ablations` below are DEPRECATED (they ignored
ranked_jobs and computed metrics directly on annotations, so every config
produced identical numbers). Kept only to avoid breaking imports. Use
`pool_eval.run_phase_a` instead.
"""

ABLATION_CONFIGS = {
    "tfidf_only": {
        "description": "TF-IDF description score only, no structured fields",
        "active_fields": ["description"],
        "ir_mode": "tfidf",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "bm25_only": {
        "description": "BM25 description score only, no structured fields",
        "active_fields": ["description"],
        "ir_mode": "bm25",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "hybrid_text": {
        "description": "TF-IDF + BM25 average (description only), no structured fields",
        "active_fields": ["description"],
        "ir_mode": "hybrid",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "dense_only": {
        "description": "Dense (OpenAI embedding) description score only, no structured fields",
        "active_fields": ["description"],
        "ir_mode": "dense",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "hybrid_rrf": {
        "description": "BM25 + Dense fused via Reciprocal Rank Fusion (description only), no structured fields",
        "active_fields": ["description"],
        "ir_mode": "hybrid_rrf",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "hybrid_rrf_reranked": {
        "description": "hybrid_rrf + LLM reranker on top-50 (description only), no structured fields",
        "active_fields": ["description"],
        "ir_mode": "hybrid_rrf",
        "use_reranker": True,
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "structured_only": {
        "description": "Structured fields only (salary, location, remote, tags), no description",
        "active_fields": ["salary", "location", "remote", "tags"],
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "all_equal_weights": {
        "description": "All fields with equal 1/6 weight",
        "active_fields": "all",
        "equal_weights": True,
        "skip_expansion": False,
        "use_category": True,
        "hard_filter_mode": False,
    },
    "all_default_weights": {
        "description": "All fields with predefined default weights",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": True,
        "hard_filter_mode": False,
        "force_default_weights": True,
    },
    "all_adaptive_weights": {
        "description": "All fields with LLM query-adaptive weights",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": True,
        "hard_filter_mode": False,
    },
    "hard_filter_baseline": {
        "description": "SQL WHERE hard filters instead of soft scoring",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": True,
        "hard_filter_mode": True,
    },
    "no_expansion": {
        "description": "All fields, query expansion disabled",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": True,
        "use_category": True,
        "hard_filter_mode": False,
    },
    "with_expansion": {
        "description": "All fields, query expansion enabled",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": True,
        "hard_filter_mode": False,
    },
    "no_category": {
        "description": "All fields except category in scoring",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": False,
        "hard_filter_mode": False,
    },
    "with_category": {
        "description": "All fields including category in scoring",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": True,
        "hard_filter_mode": False,
    },
}


def run_single_config(
    config_name: str,
    test_queries: list[dict],
    annotated_relevances: dict[str, list[int]],
) -> dict:
    """
    Run pipeline on all test queries with a given ablation config.

    Args:
        config_name: key in ABLATION_CONFIGS
        test_queries: list of query dicts from test_queries.json
        annotated_relevances: {query_id: [relevance_grades]} mapping

    Returns:
        dict with per-query metrics and averaged metrics
    """
    from src.pipeline.graph import run_pipeline
    from src.eval.metrics import compute_all_metrics, average_metrics

    config = ABLATION_CONFIGS[config_name]
    per_query = []

    for tq in test_queries:
        qid = tq["id"]
        query = tq["query"]

        relevances = annotated_relevances.get(qid, [])
        if not relevances:
            continue

        result = run_pipeline(query, config=config)

        # Compute metrics using annotated relevance
        metrics = compute_all_metrics(relevances)
        metrics["query_id"] = qid
        metrics["config"] = config_name
        per_query.append(metrics)

    avg = average_metrics(per_query)
    return {
        "config_name": config_name,
        "config_description": config.get("description", ""),
        "per_query": per_query,
        "average": avg,
    }


def run_all_ablations(
    test_queries: list[dict],
    annotated_relevances: dict[str, list[int]],
) -> dict:
    """
    Run all 10 ablation configurations.

    Returns:
        dict mapping config_name to result dict
    """
    results = {}
    for config_name in ABLATION_CONFIGS:
        print(f"Running ablation: {config_name}...")
        results[config_name] = run_single_config(
            config_name, test_queries, annotated_relevances,
        )
    return results


def format_results_table(results: dict) -> str:
    """Format ablation results as a markdown table for the report."""
    header = "| Config | Description | P@5 | P@10 | nDCG@5 | nDCG@10 |"
    separator = "|--------|-------------|-----|------|--------|---------|"
    rows = [header, separator]

    for name, res in results.items():
        avg = res.get("average", {})
        desc = res.get("config_description", "")
        p5 = avg.get("P@5", 0)
        p10 = avg.get("P@10", 0)
        n5 = avg.get("nDCG@5", 0)
        n10 = avg.get("nDCG@10", 0)
        rows.append(f"| {name} | {desc} | {p5:.3f} | {p10:.3f} | {n5:.3f} | {n10:.3f} |")

    return "\n".join(rows)
