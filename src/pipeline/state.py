"""Pipeline state schema for LangGraph."""

from typing import TypedDict


class PipelineState(TypedDict, total=False):
    # Input
    user_query: str
    api_key: str | None
    session_id: str | None  # for cross-turn preference memory; None means single-turn, stateless

    # After query_understanding
    is_job_query: bool   # False → route to reject node, skip retrieval
    needs_clarification: bool  # True → route to clarify node; too few fields filled, ask instead of guessing
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

    # After verification: valid + unknown (rejected already removed)
    verified_jobs: list[dict]
    retry_count: int    # number of retries so far, at most 1
    should_retry: bool  # transient flag used for routing

    # After classification
    classified_jobs: list[dict]

    # After answer_generation
    answer: str

    # Config
    top_k: int
    config: dict  # ablation experiment flags
