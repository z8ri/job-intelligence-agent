"""Reciprocal Rank Fusion: fuse multiple retrieval result lists by rank rather than raw score.

Scores from different retrievers are not on comparable scales (TF-IDF cosine, raw
BM25 score, and embedding cosine are all distributed differently), so a direct
weighted average lets the retriever with the largest scale dominate the ranking.
RRF only looks at each retriever's internal ranks and is therefore immune to scale
differences by construction.
"""


def reciprocal_rank_fusion(
    score_dicts: list[dict[str, float]], k: int = 60
) -> dict[str, float]:
    """
    Fuse multiple {job_id: score} result sets by rank using RRF.

    Formula: RRF(d) = sum_i 1 / (k + rank_i(d)), with rank starting at 1 (highest score = rank 1).
    A document absent from one retriever contributes 0 for that retriever (not every
    retriever recalls every document).

    Args:
        score_dicts: each retriever's {job_id: score} results; higher score means more relevant
        k: RRF constant. 60 is the standard default from the original paper
           (Cormack et al. 2009); larger values flatten the gap between lower-ranked documents

    Returns:
        {job_id: fused_score}, covering every job_id that appeared in any list
    """
    fused: dict[str, float] = {}
    for scores in score_dicts:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        for rank, (job_id, _) in enumerate(ranked, start=1):
            fused[job_id] = fused.get(job_id, 0.0) + 1.0 / (k + rank)
    return fused
