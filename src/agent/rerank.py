"""Cross-Encoder rerank of the fused candidates.

The query is the user's *work content* (role_focus + skill) only; "avoid",
location, salary etc. are checked later against evidence, so they never enter the
scorer. The passage is organised so the model sees what the job does: title, then
the best-matching responsibilities segment found during retrieval (or the start of
the text when the post has no such section).

The scorer is injectable so tests and offline runs never load a model. If scoring
fails the retrieval order is kept and the trace says so.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from src.agent.retrieval import Candidate, JobIndex
from src.agent.snapshots import Snapshot

DEFAULT_MODEL = "BAAI/bge-reranker-base"


class Scorer(Protocol):
    def score(self, pairs: list[tuple[str, str]]) -> list[float]: ...


class CrossEncoderScorer:
    """sentence-transformers CrossEncoder, loaded on first use."""

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str | None = None, batch_size: int = 16, max_length: int = 512):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name, device=self.device, max_length=self.max_length)
        return self._model

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
        scores = self._load().predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        return [float(s) for s in scores]


def build_passage(snap: Snapshot, best_segment: tuple[int, int] | None, max_chars: int = 1500) -> str:
    header = snap.title.strip()
    if snap.company:
        header += f" ({snap.company})"
    if best_segment is not None:
        start, end = best_segment
        body = snap.text[start:end]
    else:
        body = snap.text
    return f"{header}\n{body[:max_chars]}".strip()


@dataclass
class RerankResult:
    candidates: list[Candidate]
    trace: dict


def rerank(
    query: str,
    index: JobIndex,
    candidates: list[Candidate],
    scorer: Scorer,
    *,
    depth: int = 30,
    top_n: int | None = None,
    max_passage_chars: int = 1500,
) -> RerankResult:
    """Reorder the first `depth` candidates by cross-encoder score; the rest keep their
    retrieval order below them. Returns new Candidate objects (inputs are not mutated)."""
    head, tail = candidates[:depth], candidates[depth:]
    trace: dict = {"scorer": type(scorer).__name__, "reranked": len(head), "status": "ok"}

    copies = [replace(c, stage_ranks=dict(c.stage_ranks), channel_scores=dict(c.channel_scores),
                      merged_keys=list(c.merged_keys)) for c in candidates]
    head_c, tail_c = copies[:depth], copies[depth:]

    if head:
        pairs = [(query, build_passage(index.snapshot(c.job_key), c.best_segment, max_passage_chars)) for c in head]
        try:
            scores = scorer.score(pairs)
            if len(scores) != len(head):
                raise ValueError(f"scorer returned {len(scores)} scores for {len(head)} pairs")
        except Exception as e:  # keep the retrieval order rather than failing the request
            trace.update(status=f"failed: {e}", reranked=0)
            scores = None
        if scores is not None:
            order = sorted(range(len(head_c)), key=lambda i: (-scores[i], i))
            for i in range(len(head_c)):
                head_c[i].channel_scores["rerank"] = float(scores[i])
            for rank, i in enumerate(order, start=1):
                head_c[i].stage_ranks["rerank"] = rank
            head_c = [head_c[i] for i in order]

    final = head_c + tail_c
    if top_n is not None:
        final = final[:top_n]
    for rank, c in enumerate(final, start=1):
        c.stage_ranks["final"] = rank
    return RerankResult(final, trace)
