"""Unit tests for src/ir/dense.py. OpenAI client and disk I/O are mocked/redirected to
a tmp_path — no network calls, no touching the real data/dense_model.pkl.
"""

import pickle
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.ir.dense import JobDenseSystem, EMBEDDING_MODEL


def _fake_embed_response(vectors):
    """Build a fake OpenAI embeddings.create() response, deliberately out of order
    to exercise the index-based re-sort in _embed_texts.
    """
    items = [MagicMock(index=i, embedding=v) for i, v in enumerate(vectors)]
    items = list(reversed(items))  # API order != input order, worst case
    resp = MagicMock()
    resp.data = items
    return resp


class TestGetSimilarities:
    def test_reorders_by_response_index_and_normalizes_to_unit_range(self):
        system = JobDenseSystem()
        system.job_ids = ["a", "b", "c"]
        # Unit vectors along 3 axes: query aligned with "a" should score highest.
        system.embeddings = np.eye(3, dtype=np.float32)

        client = MagicMock()
        client.embeddings.create.return_value = _fake_embed_response([[1.0, 0.0, 0.0]])

        with patch("src.ir.dense.get_client", return_value=client):
            scores = system.get_similarities("query aligned with a")

        assert scores["a"] == pytest.approx(1.0)
        assert scores["c"] == pytest.approx(0.0)
        assert scores["a"] > scores["b"] > scores["c"] or scores["b"] == scores["c"]

    def test_lazily_loads_model_when_embeddings_not_yet_in_memory(self, tmp_path):
        system = JobDenseSystem()
        system.model_path = tmp_path / "dense_model.pkl"
        with open(system.model_path, "wb") as f:
            pickle.dump(
                {"job_ids": ["x"], "embeddings": np.array([[1.0, 0.0]], dtype=np.float32), "model_name": EMBEDDING_MODEL},
                f,
            )

        client = MagicMock()
        client.embeddings.create.return_value = _fake_embed_response([[1.0, 0.0]])
        with patch("src.ir.dense.get_client", return_value=client):
            scores = system.get_similarities("query")

        assert scores == {"x": pytest.approx(0.0)}  # single job → min==max → all zero, by design

    def test_missing_model_file_returns_empty_without_calling_llm(self, tmp_path):
        system = JobDenseSystem()
        system.model_path = tmp_path / "does_not_exist.pkl"
        with patch("src.ir.dense.get_client") as mock_get_client:
            scores = system.get_similarities("query")
        assert scores == {}
        mock_get_client.assert_not_called()


class TestModelPersistence:
    def test_save_then_load_round_trips_plain_data_only(self, tmp_path):
        system = JobDenseSystem()
        system.model_path = tmp_path / "dense_model.pkl"
        system.job_ids = ["a", "b"]
        system.embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        system._save_model()

        # Persisted payload must be plain data (dict/list/ndarray/str), never a
        # custom class instance — that's what caused the __main__-path pickle
        # trap already hit once with the TF-IDF model.
        with open(system.model_path, "rb") as f:
            raw = pickle.load(f)
        assert set(raw.keys()) == {"job_ids", "embeddings", "model_name"}
        assert isinstance(raw["job_ids"], list)

        reloaded = JobDenseSystem()
        reloaded.model_path = system.model_path
        assert reloaded.load_model() is True
        assert reloaded.job_ids == ["a", "b"]
        np.testing.assert_array_equal(reloaded.embeddings, system.embeddings)

    def test_load_rejects_mismatched_embedding_model(self, tmp_path):
        model_path = tmp_path / "dense_model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump({"job_ids": ["a"], "embeddings": np.zeros((1, 2)), "model_name": "some-other-model"}, f)

        system = JobDenseSystem()
        system.model_path = model_path
        with pytest.raises(ValueError):
            system.load_model()
