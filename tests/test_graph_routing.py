"""Unit tests for the routing/control-flow logic in src/pipeline/graph.py —
the actual orchestration, not the leaf scoring modules already covered
elsewhere. Pure routing functions need no mocking; node_unified_scoring's
Planner precedence is tested with the retrieval systems, scoring engine, and
LLM reranker all mocked (no DB, no OpenAI, no on-disk pickle models).
"""

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.graph import (
    _route_after_understanding,
    _route_after_verification,
    _PLANNER_MODE_MAP,
    node_unified_scoring,
)


class TestRouteAfterUnderstanding:
    def test_non_job_query_routes_to_reject_regardless_of_other_fields(self):
        state = {"is_job_query": False, "needs_clarification": True}
        assert _route_after_understanding(state) == "reject"

    def test_clarification_needed_routes_to_clarify(self):
        state = {"is_job_query": True, "needs_clarification": True}
        assert _route_after_understanding(state) == "clarify"

    def test_normal_job_query_routes_to_query_expansion(self):
        state = {"is_job_query": True, "needs_clarification": False}
        assert _route_after_understanding(state) == "query_expansion"

    def test_missing_is_job_query_defaults_to_true(self):
        # PipelineState.get("is_job_query", True) — absence must not be treated as reject.
        state = {"needs_clarification": False}
        assert _route_after_understanding(state) == "query_expansion"


class TestRouteAfterVerification:
    def test_should_retry_true_routes_to_retry(self):
        assert _route_after_verification({"should_retry": True}) == "retry"

    def test_should_retry_false_routes_to_continue(self):
        assert _route_after_verification({"should_retry": False}) == "continue"

    def test_missing_should_retry_defaults_to_continue(self):
        assert _route_after_verification({}) == "continue"


class TestPlannerModeMap:
    def test_exact_uses_bm25_without_reranker(self):
        assert _PLANNER_MODE_MAP["exact"] == {"ir_mode": "bm25", "use_reranker": False}

    def test_semantic_uses_hybrid_rrf_without_reranker(self):
        assert _PLANNER_MODE_MAP["semantic"] == {"ir_mode": "hybrid_rrf", "use_reranker": False}

    def test_exploratory_uses_hybrid_rrf_with_reranker(self):
        assert _PLANNER_MODE_MAP["exploratory"] == {"ir_mode": "hybrid_rrf", "use_reranker": True}

    def test_unrecognized_retrieval_mode_falls_back_to_empty_plan(self):
        # node_unified_scoring does _PLANNER_MODE_MAP.get(prefs.get("retrieval_mode"), {})
        assert _PLANNER_MODE_MAP.get("not_a_real_mode", {}) == {}
        assert _PLANNER_MODE_MAP.get(None, {}) == {}


def _make_job(job_id):
    return {"job_id": job_id, "title": f"Role {job_id}", "description": "desc"}


class TestUnifiedScoringPlannerPrecedence:
    """node_unified_scoring's actual precedence rule: an explicit `config["ir_mode"]`
    overrides the Planner's choice, but `use_reranker` is resolved independently —
    it only falls back to the Planner's choice when the caller didn't set it
    explicitly. That asymmetry is easy to get wrong on a future edit, so it's
    worth locking in with a test rather than only relying on the module docstring.
    """

    def _run(self, *, retrieval_mode, config, candidates=None):
        candidates = candidates or [_make_job("j1"), _make_job("j2")]
        state = {
            "preferences": {"retrieval_mode": retrieval_mode, "weight_adjustments": {}},
            "config": config,
            "expanded_keywords": [],
            "user_query": "python backend engineer",
            "candidates": candidates,
            "api_key": None,
        }

        bm25_system = MagicMock()
        bm25_system.get_similarities.return_value = {"j1": 0.8, "j2": 0.2}
        dense_system = MagicMock()
        dense_system.get_similarities.return_value = {"j1": 0.6, "j2": 0.4}
        scoring_engine = MagicMock()
        scoring_engine.compute_final_score.side_effect = lambda job, prefs, tfidf, weight_adjustments: (tfidf, {"description": tfidf})

        with patch("src.pipeline.graph._get_bm25_system", return_value=bm25_system), \
             patch("src.pipeline.graph._get_dense_system", return_value=dense_system), \
             patch("src.pipeline.graph._get_ir_system") as mock_tfidf_getter, \
             patch("src.pipeline.graph._get_scoring_engine", return_value=scoring_engine), \
             patch("src.pipeline.graph.rerank") as mock_rerank:
            mock_tfidf_getter.return_value.get_similarities.return_value = {"j1": 0.5, "j2": 0.5}
            result = node_unified_scoring(state)

        return result, bm25_system, dense_system, mock_tfidf_getter, mock_rerank

    def test_exact_mode_with_no_config_uses_bm25_only_no_reranker(self):
        result, bm25_system, dense_system, tfidf_getter, mock_rerank = self._run(
            retrieval_mode="exact", config={}
        )
        bm25_system.get_similarities.assert_called_once()
        dense_system.get_similarities.assert_not_called()
        mock_rerank.assert_not_called()
        assert result["scored_jobs"][0]["final_score"] == 0.8  # j1's bm25 score, unmodified

    def test_explicit_ir_mode_overrides_planner_but_reranker_still_inherits_from_plan(self):
        # Planner says exploratory -> hybrid_rrf + reranker=True. Caller explicitly
        # forces ir_mode="bm25" (e.g. an eval ablation config) but does NOT set
        # use_reranker — per the precedence rule, use_reranker must still come
        # from the Planner's exploratory choice (True), not silently default to False.
        result, bm25_system, dense_system, tfidf_getter, mock_rerank = self._run(
            retrieval_mode="exploratory", config={"ir_mode": "bm25"}
        )
        bm25_system.get_similarities.assert_called_once()
        dense_system.get_similarities.assert_not_called()  # bm25 mode, dense never touched
        mock_rerank.assert_called_once()  # reranker still ran, inherited from the plan

    def test_fully_explicit_config_ignores_planner_entirely(self):
        # Used by the CLI (--ir-mode/--rerank) and src/eval/* ablations: retrieval_mode
        # is irrelevant once both ir_mode and use_reranker are set explicitly.
        mock_rerank_return = {"j1": 0.99}
        result, bm25_system, dense_system, tfidf_getter, mock_rerank = self._run(
            retrieval_mode=None, config={"ir_mode": "hybrid_rrf", "use_reranker": True}
        )
        bm25_system.get_similarities.assert_called_once()
        dense_system.get_similarities.assert_called_once()
        mock_rerank.assert_called_once()

    def test_unrecognized_ir_mode_falls_back_to_tfidf(self):
        result, bm25_system, dense_system, tfidf_getter, mock_rerank = self._run(
            retrieval_mode=None, config={}
        )
        tfidf_getter.return_value.get_similarities.assert_called_once()
        bm25_system.get_similarities.assert_not_called()
