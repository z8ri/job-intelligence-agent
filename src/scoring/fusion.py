"""
Collection fusion module.

The HN and Greenhouse/Lever sources may score on different scales (e.g. HN
descriptions are longer, so their TF-IDF scores skew higher), so scores must be
normalized across sources before they can be merged and ranked fairly.

Method: group by source and apply min-max normalization, mapping each source's
scores to [0, 1].
"""


def normalize_scores(scored_jobs: list[dict], score_key: str = "final_score") -> list[dict]:
    """
    Min-max normalize the scored results, grouped by data source.

    Args:
        scored_jobs: jobs with a computed final score; each dict must contain:
            - source: str ("hackernews" / "greenhouse" / "lever")
            - final_score: float (final score before normalization)
        score_key: name of the score field

    Returns:
        The same list, with a new "normalized_score" field added to each dict.
        The original final_score is left unchanged.
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
                # All scores in this source are identical -> assign 0.5 uniformly
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
    Fusion step: by default return the top-K sorted by final_score descending.

    In practice, min-max normalization forces each source's "local best" to tie
    at 1.0, so marginal jobs from the smaller source (e.g. 'Brazil - Remote')
    keep squeezing into the top-10. normalize is therefore disabled by default;
    normalize_scores is kept as an optional baseline (enabled with normalize=True).

    Args:
        scored_jobs: list of scored jobs
        top_k: number of results to return
        score_key: name of the score field used for sorting
        normalize: if True, min-max normalize per source before sorting (legacy behavior)
        dedupe: if True, dedupe by (company, title). The monthly HN threads cause the
            same posting to be stored under multiple job_ids. The evaluation
            pool_eval does not pass this flag so its behavior is unchanged; the
            demo path in graph.py enables it by default

    Returns:
        top-K job list, sorted descending by score_key (or normalized_score when normalized)
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
