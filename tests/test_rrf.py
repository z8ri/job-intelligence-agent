"""Unit tests for src/ir/rrf.py — Reciprocal Rank Fusion. Pure function, no mocking needed."""

from src.ir.rrf import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_single_list_preserves_rank_order(self):
        scores = {"a": 0.9, "b": 0.5, "c": 0.1}
        fused = reciprocal_rank_fusion([scores])
        assert fused["a"] > fused["b"] > fused["c"]

    def test_agreement_across_lists_boosts_score(self):
        # "a" is top-ranked in both lists; "b" only appears in one.
        list1 = {"a": 1.0, "b": 0.5}
        list2 = {"a": 1.0, "c": 0.5}
        fused = reciprocal_rank_fusion([list1, list2])
        assert fused["a"] > fused["b"]
        assert fused["a"] > fused["c"]

    def test_missing_from_one_list_contributes_zero_from_that_source(self):
        list1 = {"a": 1.0, "b": 0.9}
        list2 = {"a": 1.0}
        fused = reciprocal_rank_fusion([list1, list2])
        # "a" ranks 1st in both lists: 2 * 1/(60+1)
        assert abs(fused["a"] - 2 / 61) < 1e-9
        # "b" ranks 2nd in list1 only, absent from list2.
        assert abs(fused["b"] - 1 / 62) < 1e-9

    def test_custom_k_changes_magnitude_not_order(self):
        scores = {"a": 0.9, "b": 0.5}
        fused_default = reciprocal_rank_fusion([scores])
        fused_small_k = reciprocal_rank_fusion([scores], k=1)
        assert fused_small_k["a"] > fused_default["a"]
        assert fused_small_k["a"] > fused_small_k["b"]

    def test_empty_input_returns_empty(self):
        assert reciprocal_rank_fusion([]) == {}

    def test_result_covers_union_of_all_ids(self):
        fused = reciprocal_rank_fusion([{"a": 1.0}, {"b": 1.0}, {"c": 1.0}])
        assert set(fused.keys()) == {"a", "b", "c"}
