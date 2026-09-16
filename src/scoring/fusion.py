"""
Collection Fusion 模块

HN 与 Greenhouse/Lever 两个数据源的评分尺度可能不同（例如 HN 的描述更长，
TF-IDF 得分分布偏高），需要跨源归一化后才能公平合并排序。

方法：按 source 分组做 Min-Max 归一化，将各源的分数统一到 [0, 1]。
"""


def normalize_scores(scored_jobs: list[dict], score_key: str = "final_score") -> list[dict]:
    """
    对评分结果按数据源分组做 Min-Max 归一化。

    Args:
        scored_jobs: 已计算综合得分的职位列表，每个 dict 需包含:
            - source: str ("hackernews" / "greenhouse" / "lever")
            - final_score: float (归一化前的综合得分)
        score_key: 得分字段名

    Returns:
        相同列表，每个 dict 新增 "normalized_score" 字段。
        原始 final_score 保留不变。
    """
    groups: dict[str, list[dict]] = {}
    for job in scored_jobs:
        src = job.get("source", "unknown")
        groups.setdefault(src, []).append(job)

    for src, jobs in groups.items():
        scores = [j[score_key] for j in jobs]
        min_s = min(scores)
        max_s = max(scores)
        spread = max_s - min_s

        for job in jobs:
            if spread > 0:
                job["normalized_score"] = (job[score_key] - min_s) / spread
            else:
                # 该源所有分数相同 → 统一给 0.5
                job["normalized_score"] = 0.5

    return scored_jobs


def fuse_and_rank(
    scored_jobs: list[dict],
    top_k: int = 10,
    score_key: str = "final_score",
    normalize: bool = False,
    dedupe: bool = False,
) -> list[dict]:
    """
    fusion 流程：默认按 final_score 降序返回 top-K。

    实测 min-max 归一化会让两源的"局部最佳"被强制并列 1.0，导致小源的边缘工作
    （如 'Brazil - Remote'）反复挤进 top-10。因此默认禁用 normalize；
    保留 normalize_scores 作为可选基线（normalize=True 时启用）。

    Args:
        scored_jobs: 已评分的职位列表
        top_k: 返回的结果数
        score_key: 排序使用的得分字段名
        normalize: True 时按 source 做 min-max 归一化后排序（旧行为）
        dedupe: True 时按 (company, title) 去重 — HN 月度帖会让同一岗位以多
            job_id 入库；evaluation pool_eval 不传该参数以保持原行为不变，
            graph.py 的 demo 路径默认开启

    Returns:
        top-K 职位列表，按 score_key（或归一化后 normalized_score）降序排列
    """
    if normalize:
        normalize_scores(scored_jobs, score_key)
        scored_jobs.sort(key=lambda j: j.get("normalized_score", 0), reverse=True)
    else:
        scored_jobs.sort(key=lambda j: j.get(score_key, 0), reverse=True)

    if dedupe:
        seen: set[tuple[str, str]] = set()
        out: list[dict] = []
        for job in scored_jobs:
            company = (job.get("company") or "").strip().lower()
            title = (job.get("title") or "").strip().lower()
            key = (company, title)
            if key in seen:
                continue
            seen.add(key)
            out.append(job)
            if len(out) >= top_k:
                break
        return out

    return scored_jobs[:top_k]
