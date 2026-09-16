"""Reciprocal Rank Fusion：按名次而非原始分数融合多路检索结果。

不同检索器的分数尺度不可比（TF-IDF cosine、BM25 raw score、embedding cosine
分布都不同），直接加权平均会让尺度大的一路主导排序。RRF 只看每路内部的名次，
天然免疫尺度差异。
"""


def reciprocal_rank_fusion(
    score_dicts: list[dict[str, float]], k: int = 60
) -> dict[str, float]:
    """
    对多路 {job_id: score} 结果按名次做 RRF 融合。

    公式：RRF(d) = sum_i 1 / (k + rank_i(d))，rank 从 1 开始（分数最高者 rank=1）。
    某路里没出现的文档在该路贡献 0（不是所有检索器都会召回所有文档）。

    Args:
        score_dicts: 每路检索器的 {job_id: score} 结果，score 降序表示更相关
        k: RRF 常数，60 是原始论文（Cormack et al. 2009）的标准默认值，
           越大则名次靠后的文档差距被压得越平

    Returns:
        {job_id: fused_score}，覆盖所有出现过的 job_id
    """
    fused: dict[str, float] = {}
    for scores in score_dicts:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        for rank, (job_id, _) in enumerate(ranked, start=1):
            fused[job_id] = fused.get(job_id, 0.0) + 1.0 / (k + rank)
    return fused
