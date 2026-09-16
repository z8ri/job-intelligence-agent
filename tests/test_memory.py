"""Unit tests for src/db/memory.py. MySQL connection is mocked — no real database
required. merge_preferences is pure and needs no mocking at all.
"""

import json
from unittest.mock import MagicMock, patch

from src.db.memory import load_memory, save_memory, merge_preferences


def _fake_conn(fetchone_result=None):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_result
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    return conn, cur


class TestMergePreferences:
    def test_current_field_wins_when_explicitly_mentioned(self):
        current = {"target_salary": 200000}
        memory = {"target_salary": 150000}
        merged = merge_preferences(current, memory)
        assert merged["target_salary"] == 200000

    def test_falls_back_to_memory_when_current_is_empty(self):
        current = {"target_salary": None, "remote_preference": None}
        memory = {"target_salary": 150000, "remote_preference": "remote"}
        merged = merge_preferences(current, memory)
        assert merged["target_salary"] == 150000
        assert merged["remote_preference"] == "remote"

    def test_per_utterance_fields_never_inherit_from_memory(self):
        # weight_adjustments / is_job_query / retrieval_mode represent a judgment
        # about *this* utterance and must never be carried over silently.
        current = {"weight_adjustments": {}, "is_job_query": True, "retrieval_mode": "exploratory"}
        memory = {"weight_adjustments": {"salary": "high"}, "is_job_query": False, "retrieval_mode": "exact"}
        merged = merge_preferences(current, memory)
        assert merged["weight_adjustments"] == {}
        assert merged["is_job_query"] is True
        assert merged["retrieval_mode"] == "exploratory"

    def test_empty_list_and_dict_are_treated_as_unset(self):
        current = {"desired_tags": [], "hard_filters": []}
        memory = {"desired_tags": ["Python"], "hard_filters": [{"field": "degree_req"}]}
        merged = merge_preferences(current, memory)
        assert merged["desired_tags"] == ["Python"]
        assert merged["hard_filters"] == [{"field": "degree_req"}]

    def test_no_memory_returns_current_unchanged(self):
        current = {"target_salary": 150000, "preferred_location": "NYC"}
        merged = merge_preferences(current, {})
        assert merged == current


class TestLoadMemory:
    def test_returns_empty_dict_when_no_row(self):
        conn, _ = _fake_conn(fetchone_result=None)
        with patch("src.db.memory.get_connection", return_value=conn):
            result = load_memory("session_without_history")
        assert result == {}
        conn.close.assert_called_once()

    def test_parses_stored_json_preferences(self):
        stored = {"target_salary": 150000, "remote_preference": "remote"}
        conn, _ = _fake_conn(fetchone_result={"preferences": json.dumps(stored)})
        with patch("src.db.memory.get_connection", return_value=conn):
            result = load_memory("session_with_history")
        assert result == stored


class TestSaveMemory:
    def test_only_persists_whitelisted_fields(self):
        conn, cur = _fake_conn()
        prefs = {
            "target_salary": 150000,
            "is_job_query": True,          # not in _MEMORY_FIELDS — must not leak into storage
            "weight_adjustments": {"salary": "high"},  # same
        }
        with patch("src.db.memory.get_connection", return_value=conn):
            save_memory("s1", prefs)

        args, _ = cur.execute.call_args
        stored_json = args[1][1]
        stored = json.loads(stored_json)
        assert stored["target_salary"] == 150000
        assert "is_job_query" not in stored
        assert "weight_adjustments" not in stored
        conn.commit.assert_called_once()
        conn.close.assert_called_once()
