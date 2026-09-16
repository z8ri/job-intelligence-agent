"""Pipeline state schema for LangGraph."""

from typing import TypedDict


class PipelineState(TypedDict, total=False):
    # Input
    user_query: str
    api_key: str | None
    session_id: str | None  # 跨轮偏好记忆用，None 时行为等同单轮无状态

    # After query_understanding
    is_job_query: bool   # False → route to reject node, skip retrieval
    needs_clarification: bool  # True → route to clarify node，字段太空反问而不是瞎猜
    preferences: dict
    weights: dict

    # After query_expansion
    expanded_keywords: list[str] | None
    expanded_tags: list[str] | None

    # After candidate_loading
    candidates: list[dict]

    # After unified_scoring
    scored_jobs: list[dict]

    # After collection_fusion
    ranked_jobs: list[dict]

    # After verification：valid+unknown（rejected 已剔除）
    verified_jobs: list[dict]
    retry_count: int    # 已重试次数，最多 1
    should_retry: bool  # 路由用的临时标记

    # After classification
    classified_jobs: list[dict]

    # After answer_generation
    answer: str

    # Config
    top_k: int
    config: dict  # ablation experiment flags
