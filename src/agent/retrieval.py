"""Three-channel candidate retrieval fused with RRF.

Channels:
  bm25        lexical match over title (x2) + normalized text
  dense_resp  semantic match against the responsibilities segments only, so a job
              that merely lists a skill under "requirements" does not look like a
              job that does the work
  dense_full  semantic match over title + the start of the full text (catches
              posts that have no recognisable sections, e.g. free-form HN posts)

Only jobs recalled by a channel enter its ranking, and RRF fuses by rank, so the
scales of BM25 and cosine never have to be compared. Every candidate keeps its rank
in each stage so a later ranking change can be explained.

If embeddings are unavailable the search degrades to BM25 and says so in the trace.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from nltk.stem import PorterStemmer
from rank_bm25 import BM25Okapi

from src.agent.embeddings import CachedEmbedder, EmbeddingError
from src.agent.snapshots import Snapshot, canonical_url
from src.ir.rrf import reciprocal_rank_fusion

_STEMMER = PorterStemmer()
_STOP = frozenset(
    "a an and are as at be but by for from has have in is it its of on or our that the their "
    "this to we will with you your about into over than then them they who what which while "
    "can may also any all more most other such not no how us if so do does did been being were was".split()
)
_TOKEN = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*(?:\+\+|#)?")
_KEEP_SINGLE = {"c", "r"}


@lru_cache(maxsize=100_000)
def _stem(word: str) -> str:
    return _STEMMER.stem(word) if word.isalpha() else word


def tokenize(text: str) -> list[str]:
    """Lowercase, keep technical tokens (c++, c#, node.js), split hyphens, stem, drop stopwords."""
    out = []
    for tok in _TOKEN.findall((text or "").lower()):
        if tok in _STOP or (len(tok) == 1 and tok not in _KEEP_SINGLE):
            continue
        out.append(_stem(tok))
    return out


@dataclass
class Candidate:
    job_key: str
    score: float
    stage_ranks: dict[str, int] = field(default_factory=dict)
    channel_scores: dict[str, float] = field(default_factory=dict)
    merged_keys: list[str] = field(default_factory=list)
    # character span (in the normalized text) of the best-matching responsibilities segment
    best_segment: tuple[int, int] | None = None


@dataclass
class RetrievalResult:
    candidates: list[Candidate]
    trace: dict


class JobIndex:
    def __init__(
        self,
        snapshots: list[Snapshot],
        embedder: CachedEmbedder | None = None,
        *,
        full_text_chars: int = 6000,
        segment_chars: int = 2000,
    ):
        self._snaps = {s.job_key: s for s in sorted(snapshots, key=lambda s: s.job_key)}
        self._keys = list(self._snaps)
        self._embedder = embedder
        self._full_text_chars = full_text_chars
        self._segment_chars = segment_chars

        corpus = [tokenize(f"{s.title} {s.title} {s.text}") for s in self._snaps.values()]
        self._bm25 = BM25Okapi(corpus) if corpus else None

        self._dense_lock = threading.Lock()
        self._full_matrix: np.ndarray | None = None
        self._seg_matrix: np.ndarray | None = None
        self._seg_owner: list[int] = []
        self._seg_span: list[tuple[int, int]] = []

    def __len__(self) -> int:
        return len(self._keys)

    def snapshot(self, job_key: str) -> Snapshot:
        return self._snaps[job_key]

    def _ensure_dense(self) -> None:
        with self._dense_lock:
            if self._full_matrix is not None or not self._keys:
                return
            assert self._embedder is not None
            full_texts = [
                f"{s.title}\n{s.text[: self._full_text_chars]}" for s in self._snaps.values()
            ]
            seg_texts: list[str] = []
            owners: list[int] = []
            spans: list[tuple[int, int]] = []
            for i, s in enumerate(self._snaps.values()):
                for seg in s.segments():
                    if seg.kind == "responsibilities":
                        seg_texts.append(f"{s.title}\n{seg.text[: self._segment_chars]}")
                        owners.append(i)
                        spans.append((seg.start, seg.end))
            full = self._embedder.embed(full_texts)
            seg = self._embedder.embed(seg_texts) if seg_texts else None
            self._seg_matrix, self._seg_owner, self._seg_span = seg, owners, spans
            self._full_matrix = full

    def _bm25_channel(self, query: str, depth: int) -> dict[str, float]:
        tokens = tokenize(query)
        if not tokens or self._bm25 is None:
            return {}
        scores = self._bm25.get_scores(tokens)
        return _top(self._keys, scores, depth, positive_only=True)

    def _dense_channels(self, query: str, depth: int) -> tuple[dict[str, float], dict[str, float], dict[str, tuple[int, int]]]:
        self._ensure_dense()
        qvec = self._embedder.embed([query])[0]  # type: ignore[union-attr]
        full_scores = self._full_matrix @ qvec  # type: ignore[operator]
        full = _top(self._keys, full_scores, depth)

        resp: dict[str, float] = {}
        spans: dict[str, tuple[int, int]] = {}
        if self._seg_matrix is not None:
            seg_scores = self._seg_matrix @ qvec
            best: dict[int, int] = {}
            for j, owner in enumerate(self._seg_owner):
                if owner not in best or seg_scores[j] > seg_scores[best[owner]]:
                    best[owner] = j
            per_job = np.full(len(self._keys), -np.inf)
            for owner, j in best.items():
                per_job[owner] = seg_scores[j]
            resp = _top(self._keys, per_job, depth, finite_only=True)
            spans = {self._keys[o]: self._seg_span[j] for o, j in best.items() if self._keys[o] in resp}
        return resp, full, spans

    def search(self, query: str, *, top_n: int = 50, channel_depth: int = 100, rrf_k: int = 60) -> RetrievalResult:
        trace: dict = {"query": query, "channels": {}}
        if not self._keys:
            trace.update(degraded=[], embedding={"hits": 0, "misses": 0}, fused=0, deduped=0)
            return RetrievalResult([], trace)
        before = self._embedder.stats() if self._embedder else {"hits": 0, "misses": 0}

        channels: dict[str, dict[str, float]] = {"bm25": self._bm25_channel(query, channel_depth)}
        trace["channels"]["bm25"] = {"status": "ok", "recalled": len(channels["bm25"])}
        spans: dict[str, tuple[int, int]] = {}

        if self._embedder is None:
            for name in ("dense_resp", "dense_full"):
                trace["channels"][name] = {"status": "skipped: no embedder"}
        else:
            try:
                resp, full, spans = self._dense_channels(query, channel_depth)
                channels["dense_resp"], channels["dense_full"] = resp, full
                trace["channels"]["dense_resp"] = {"status": "ok", "recalled": len(resp)}
                trace["channels"]["dense_full"] = {"status": "ok", "recalled": len(full)}
            except EmbeddingError as e:
                for name in ("dense_resp", "dense_full"):
                    trace["channels"][name] = {"status": f"failed: {e}"}
        trace["degraded"] = sorted(n for n in ("dense_resp", "dense_full") if n not in channels)

        after = self._embedder.stats() if self._embedder else before
        trace["embedding"] = {k: after[k] - before[k] for k in ("hits", "misses")}

        stage_ranks = {name: {k: r for r, k in enumerate(scores, start=1)} for name, scores in channels.items()}
        fused = reciprocal_rank_fusion([c for c in channels.values() if c], k=rrf_k)
        ordered = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))
        trace["fused"] = len(ordered)

        seen_urls: dict[str, Candidate] = {}
        result: list[Candidate] = []
        merged = 0
        for rrf_rank, (key, score) in enumerate(ordered, start=1):
            url = canonical_url(self._snaps[key].url)
            if url is not None and url in seen_urls:
                seen_urls[url].merged_keys.append(key)
                merged += 1
                continue
            cand = Candidate(
                job_key=key,
                score=score,
                stage_ranks={n: r[key] for n, r in stage_ranks.items() if key in r} | {"rrf": rrf_rank},
                channel_scores={n: channels[n][key] for n in channels if key in channels[n]},
                best_segment=spans.get(key),
            )
            if url is not None:
                seen_urls[url] = cand
            result.append(cand)
        trace["deduped"] = merged

        result = result[:top_n]
        for final_rank, cand in enumerate(result, start=1):
            cand.stage_ranks["final"] = final_rank
        return RetrievalResult(result, trace)


def _top(
    keys: list[str],
    scores,
    depth: int,
    *,
    positive_only: bool = False,
    finite_only: bool = False,
) -> dict[str, float]:
    """Top `depth` {key: score}, ordered by score desc then key asc (deterministic)."""
    scores = np.asarray(scores, dtype=np.float64)
    idx = [
        i for i in range(len(keys))
        if not (positive_only and scores[i] <= 0) and not (finite_only and not np.isfinite(scores[i]))
    ]
    idx.sort(key=lambda i: (-scores[i], keys[i]))
    return {keys[i]: float(scores[i]) for i in idx[:depth]}
