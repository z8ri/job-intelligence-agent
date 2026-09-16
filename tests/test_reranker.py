"""Unit tests for src/scoring/reranker.py. OpenAI client is mocked — no network calls,
no API cost, deterministic.
"""

import json
from unittest.mock import MagicMock, patch

from src.scoring.reranker import rerank


def _candidates(n=3):
    return [
        {"job_id": f"j{i}", "title": f"Title {i}", "description": f"Description {i} " * 50}
        for i in range(n)
    ]


def _fake_client(content: str):
    client = MagicMock()
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=content))]
    client.chat.completions.create.return_value = resp
    return client


class TestRerank:
    def test_empty_candidates_returns_empty_without_calling_llm(self):
        with patch("src.scoring.reranker.get_client") as mock_get_client:
            result = rerank("some query", [])
        assert result == {}
        mock_get_client.assert_not_called()

    def test_valid_scores_are_parsed_and_clamped(self):
        content = json.dumps({"j0": 0.9, "j1": 1.5, "j2": -0.2})
        with patch("src.scoring.reranker.get_client", return_value=_fake_client(content)):
            result = rerank("python backend", _candidates(3))
        assert result["j0"] == 0.9
        assert result["j1"] == 1.0  # clamped to [0, 1]
        assert result["j2"] == 0.0  # clamped to [0, 1]

    def test_ids_not_in_candidates_are_ignored(self):
        content = json.dumps({"j0": 0.8, "hallucinated_id": 0.5})
        with patch("src.scoring.reranker.get_client", return_value=_fake_client(content)):
            result = rerank("query", _candidates(3))
        assert "hallucinated_id" not in result
        assert result["j0"] == 0.8

    def test_non_numeric_score_is_skipped(self):
        content = json.dumps({"j0": "not a number", "j1": 0.5})
        with patch("src.scoring.reranker.get_client", return_value=_fake_client(content)):
            result = rerank("query", _candidates(3))
        assert "j0" not in result
        assert result["j1"] == 0.5

    def test_malformed_json_degrades_to_empty_dict(self):
        with patch("src.scoring.reranker.get_client", return_value=_fake_client("not json")):
            result = rerank("query", _candidates(3))
        assert result == {}

    def test_client_exception_degrades_to_empty_dict(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("network error")
        with patch("src.scoring.reranker.get_client", return_value=client):
            result = rerank("query", _candidates(3))
        assert result == {}

    def test_only_scores_top_n_candidates(self):
        content = json.dumps({"j0": 0.5})
        with patch("src.scoring.reranker.get_client", return_value=_fake_client(content)):
            # top_n=1 means only j0 is ever sent to the LLM
            result = rerank("query", _candidates(5), top_n=1)
        assert set(result.keys()) <= {"j0"}
