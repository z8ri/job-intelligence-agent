"""Dense retrieval: use OpenAI embeddings to recover semantically related jobs that
lexical BM25/TF-IDF retrieval misses.

Example: the query says "LLM Agent" while the job description says "build
LLM-powered workflows with tool use and retrieval". No shared terms, so BM25/TF-IDF
cannot recall it, yet it is highly relevant semantically.

The artifact pickles plain data only (job_ids / embeddings array / model_name
string), never instances of custom classes. This avoids the pickle problem tfidf.py
once hit, where the pickled class path depended on __main__.
"""

import pickle
from pathlib import Path

import numpy as np

from src.llm import EMBEDDING_MODEL, get_client

_EMBED_BATCH_SIZE = 100


def _embed_texts(client, texts: list[str]) -> np.ndarray:
    """Call the embeddings API in batches; returns an L2-normalized matrix in input order."""
    vectors: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        # The API returns results in input order, but each item carries its own
        # index; sort by it as a safeguard against the subtle bug of job_ids and
        # vectors getting misaligned.
        ordered = sorted(resp.data, key=lambda item: item.index)
        vectors.extend(item.embedding for item in ordered)

    matrix = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class JobDenseSystem:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.model_path = self.data_dir / "dense_model.pkl"

        self.job_ids: list[str] = []
        self.embeddings: np.ndarray | None = None  # (N, dim), rows L2-normalized

    def train_from_db(self, api_key: str | None = None) -> None:
        from src.db.database import load_candidates

        jobs = load_candidates()
        texts = [f"{j.get('title', '')} {j.get('description', '')}" for j in jobs]
        self.job_ids = [j["job_id"] for j in jobs]

        print(f"Embedding {len(texts)} jobs with {EMBEDDING_MODEL}...")
        client = get_client(api_key)
        self.embeddings = _embed_texts(client, texts)

        self._save_model()
        print(f"Dense model serialized to: {self.model_path}")

    def _save_model(self) -> None:
        with open(self.model_path, "wb") as f:
            pickle.dump(
                {
                    "job_ids": self.job_ids,
                    "embeddings": self.embeddings,
                    "model_name": EMBEDDING_MODEL,
                },
                f,
            )

    def load_model(self) -> bool:
        if not self.model_path.exists():
            print("Dense model not found; run train_from_db() first")
            return False
        with open(self.model_path, "rb") as f:
            data = pickle.load(f)

        saved_model = data.get("model_name")
        if saved_model != EMBEDDING_MODEL:
            raise ValueError(
                f"{self.model_path} was built with '{saved_model}', "
                f"which does not match the current EMBEDDING_MODEL='{EMBEDDING_MODEL}'. "
                "The two models' vector spaces are not comparable; using it would yield meaningless similarities. "
                "Re-run train_from_db() to rebuild the index."
            )

        self.job_ids = data["job_ids"]
        self.embeddings = data["embeddings"]
        return True

    def get_similarities(self, query_text: str, api_key: str | None = None) -> dict[str, float]:
        if self.embeddings is None:
            if not self.load_model():
                return {}

        client = get_client(api_key)
        query_vec = _embed_texts(client, [query_text])[0]

        scores = self.embeddings @ query_vec  # rows are normalized, so dot product == cosine

        s_min, s_max = float(scores.min()), float(scores.max())
        if s_max <= s_min:
            return {jid: 0.0 for jid in self.job_ids}
        norm = (scores - s_min) / (s_max - s_min)
        return {jid: float(s) for jid, s in zip(self.job_ids, norm)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Train dense (OpenAI embedding) index from MySQL jobs table"
    )
    parser.add_argument(
        "--train", action="store_true",
        help="train the dense index (training runs regardless; the flag exists for scripting)",
    )
    parser.parse_args()

    dense_system = JobDenseSystem()
    dense_system.train_from_db()
    print("\nTest query: 'build LLM-powered workflows with tool use and retrieval'")
    scores = dense_system.get_similarities(
        "build LLM-powered workflows with tool use and retrieval"
    )
    top = sorted(scores.items(), key=lambda x: -x[1])[:5]
    for jid, s in top:
        print(f"  {jid}: {s:.4f}")
