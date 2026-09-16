"""
IR evaluation metrics: P@K and nDCG@K.

Relevance levels: 0 = not relevant, 1 = partially relevant, 2 = highly relevant.
For precision, levels 1 and 2 are treated as relevant (binary).
For nDCG, graded relevance is used directly.
"""

from math import log2


def precision_at_k(relevances: list[int], k: int) -> float:
    """
    Precision@K: fraction of top-K results that are relevant.

    Binarizes graded relevance: 0 → not relevant, 1/2 → relevant.

    Args:
        relevances: list of relevance grades in ranked order
        k: cutoff position

    Returns:
        float in [0, 1]
    """
    if k <= 0:
        return 0.0
    top_k = relevances[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for r in top_k if r > 0)
    return relevant_count / k


def dcg_at_k(relevances: list[int], k: int) -> float:
    """
    Discounted Cumulative Gain @ K.

    Formula: sum of (2^rel_i - 1) / log2(i + 2) for i in [0, k).

    Args:
        relevances: list of relevance grades in ranked order
        k: cutoff position

    Returns:
        DCG value (non-negative float)
    """
    if k <= 0:
        return 0.0
    top_k = relevances[:k]
    dcg = 0.0
    for i, rel in enumerate(top_k):
        dcg += (2 ** rel - 1) / log2(i + 2)
    return dcg


def ndcg_at_k(relevances: list[int], k: int) -> float:
    """
    Normalized DCG @ K.

    Computes DCG@K divided by ideal DCG@K (relevances sorted descending).

    Args:
        relevances: list of relevance grades in ranked order
        k: cutoff position

    Returns:
        float in [0, 1], or 0.0 if ideal DCG is 0
    """
    actual_dcg = dcg_at_k(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    ideal_dcg = dcg_at_k(ideal_relevances, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def compute_all_metrics(
    relevances: list[int],
    k_values: list[int] | None = None,
) -> dict:
    """
    Compute P@K and nDCG@K for all specified K values.

    Args:
        relevances: list of relevance grades in ranked order
        k_values: cutoff values (default: [5, 10])

    Returns:
        dict like {"P@5": 0.6, "P@10": 0.4, "nDCG@5": 0.73, "nDCG@10": 0.65}
    """
    if k_values is None:
        k_values = [5, 10]

    results = {}
    for k in k_values:
        results[f"P@{k}"] = precision_at_k(relevances, k)
        results[f"nDCG@{k}"] = ndcg_at_k(relevances, k)
    return results


def average_metrics(
    all_query_metrics: list[dict],
) -> dict:
    """
    Average metrics across multiple queries.

    Args:
        all_query_metrics: list of dicts from compute_all_metrics()

    Returns:
        dict with mean value for each metric key
    """
    if not all_query_metrics:
        return {}

    numeric_keys = [
        k for k in all_query_metrics[0]
        if isinstance(all_query_metrics[0][k], (int, float))
    ]
    averaged = {}
    for key in numeric_keys:
        values = [m[key] for m in all_query_metrics if key in m]
        averaged[key] = sum(values) / len(values) if values else 0.0
    return averaged
