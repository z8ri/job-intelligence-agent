"""Embedding access with a persistent cache.

Vectors are keyed by sha256(model + text), so unchanged job text is never
re-embedded and switching model can never mix vector spaces. Each batch is
written to the cache as soon as it returns, so a mid-run failure keeps progress.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Callable

import numpy as np

EmbedFn = Callable[[list[str]], np.ndarray]

_BATCH = 100


class EmbeddingError(RuntimeError):
    pass


def openai_embed_fn() -> EmbedFn:
    """Wrap the existing OpenAI embedding call (rows come back L2-normalized)."""
    from src.ir.dense import _embed_texts
    from src.llm import get_client

    def embed(texts: list[str]) -> np.ndarray:
        return _embed_texts(get_client(), texts)

    return embed


def default_model_name() -> str:
    from src.llm import EMBEDDING_MODEL

    return EMBEDDING_MODEL


class EmbeddingCache:
    def __init__(self, path: str | Path = ":memory:"):
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, dim INTEGER NOT NULL, vec BLOB NOT NULL)"
            )

    @staticmethod
    def key(model: str, text: str) -> str:
        return hashlib.sha256(f"{model}\x1f{text}".encode()).hexdigest()

    def get_many(self, keys: list[str]) -> dict[str, np.ndarray]:
        found: dict[str, np.ndarray] = {}
        with self._lock:
            for i in range(0, len(keys), 500):
                chunk = keys[i : i + 500]
                marks = ",".join("?" * len(chunk))
                rows = self._conn.execute(f"SELECT key, vec FROM embeddings WHERE key IN ({marks})", chunk)
                for k, blob in rows:
                    found[k] = np.frombuffer(blob, dtype=np.float32)
        return found

    def put_many(self, items: dict[str, np.ndarray]) -> None:
        rows = [(k, int(v.shape[0]), np.asarray(v, dtype=np.float32).tobytes()) for k, v in items.items()]
        with self._lock:
            self._conn.executemany("INSERT OR REPLACE INTO embeddings (key, dim, vec) VALUES (?,?,?)", rows)
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class CachedEmbedder:
    def __init__(self, embed_fn: EmbedFn, model: str, cache: EmbeddingCache | None = None):
        self.embed_fn = embed_fn
        self.model = model
        self.cache = cache or EmbeddingCache()
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def embed(self, texts: list[str]) -> np.ndarray:
        """Rows are unit vectors in input order. Identical texts are embedded once."""
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        keys = [self.cache.key(self.model, t) for t in texts]
        unique = list(dict.fromkeys(keys))
        found = self.cache.get_many(unique)
        missing = [k for k in unique if k not in found]

        text_of = dict(zip(keys, texts))
        for i in range(0, len(missing), _BATCH):
            batch_keys = missing[i : i + _BATCH]
            try:
                vecs = self.embed_fn([text_of[k] for k in batch_keys])
            except Exception as e:
                raise EmbeddingError(f"embedding call failed: {e}") from e
            if len(vecs) != len(batch_keys):
                raise EmbeddingError(f"expected {len(batch_keys)} vectors, got {len(vecs)}")
            batch = {k: np.asarray(v, dtype=np.float32) for k, v in zip(batch_keys, vecs)}
            self.cache.put_many(batch)
            found.update(batch)

        with self._lock:
            self.hits += len(unique) - len(missing)
            self.misses += len(missing)
        return np.stack([found[k] for k in keys])

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"hits": self.hits, "misses": self.misses}
