import pytest

from src.agent.rerank import CrossEncoderScorer, build_passage, rerank
from src.agent.retrieval import Candidate, JobIndex
from src.agent.snapshots import Snapshot


def job(job_id, title, body, company=""):
    return Snapshot.create(
        source="greenhouse", source_job_id=job_id, title=title, company=company, raw_content=body,
        fetched_at="2026-03-01T00:00:00+00:00",
    )


A = job("1", "Applied AI Engineer",
        "<p>Intro</p><h3>What you'll do</h3><p>Build agents</p><h3>What you should have</h3><p>Python</p>", "Acme")
B = job("2", "Backend Engineer", "Plain text post with no sections at all.")
C = job("3", "Data Engineer", "<h3>What you'll do</h3><p>Pipelines</p>")


class FakeScorer:
    def __init__(self, fn):
        self.fn = fn
        self.pairs = None

    def score(self, pairs):
        self.pairs = pairs
        return [self.fn(q, p) for q, p in pairs]


def cands(*keys):
    return [Candidate(job_key=k, score=1.0 / (i + 1), stage_ranks={"rrf": i + 1, "final": i + 1}) for i, k in enumerate(keys)]


@pytest.fixture
def index():
    return JobIndex([A, B, C])


def test_passage_uses_best_segment_and_excludes_requirements():
    seg = next(s for s in A.segments() if s.kind == "responsibilities")
    passage = build_passage(A, (seg.start, seg.end))
    assert passage.startswith("Applied AI Engineer (Acme)")
    assert "Build agents" in passage and "Python" not in passage


def test_passage_falls_back_to_text_start_and_truncates():
    long = job("9", "T", "x" * 5000)
    passage = build_passage(long, None, max_chars=100)
    assert passage == "T\n" + "x" * 100


def test_rerank_reorders_by_score_and_records_ranks(index):
    scorer = FakeScorer(lambda q, p: {"Applied": 0.1, "Backend": 0.9, "Data": 0.5}[p.split()[0]])
    res = rerank("agents", index, cands("greenhouse:1", "greenhouse:2", "greenhouse:3"), scorer)
    assert [c.job_key for c in res.candidates] == ["greenhouse:2", "greenhouse:3", "greenhouse:1"]
    assert [c.stage_ranks["rerank"] for c in res.candidates] == [1, 2, 3]
    assert [c.stage_ranks["final"] for c in res.candidates] == [1, 2, 3]
    assert res.candidates[2].stage_ranks["rrf"] == 1  # earlier stage ranks are preserved
    assert res.candidates[0].channel_scores["rerank"] == 0.9


def test_query_is_passed_verbatim_to_scorer(index):
    scorer = FakeScorer(lambda q, p: 0.0)
    rerank("LLM agents", index, cands("greenhouse:1"), scorer)
    assert scorer.pairs[0][0] == "LLM agents"


def test_ties_keep_retrieval_order(index):
    res = rerank("q", index, cands("greenhouse:3", "greenhouse:1", "greenhouse:2"), FakeScorer(lambda q, p: 0.5))
    assert [c.job_key for c in res.candidates] == ["greenhouse:3", "greenhouse:1", "greenhouse:2"]


def test_depth_limits_scoring_and_tail_stays_below(index):
    scorer = FakeScorer(lambda q, p: 1.0 if p.startswith("Backend") else 0.0)
    res = rerank("q", index, cands("greenhouse:1", "greenhouse:2", "greenhouse:3"), scorer, depth=2)
    assert len(scorer.pairs) == 2
    assert [c.job_key for c in res.candidates] == ["greenhouse:2", "greenhouse:1", "greenhouse:3"]
    assert "rerank" not in res.candidates[2].stage_ranks


def test_top_n_truncates_after_reranking(index):
    scorer = FakeScorer(lambda q, p: 1.0 if p.startswith("Data") else 0.0)
    res = rerank("q", index, cands("greenhouse:1", "greenhouse:2", "greenhouse:3"), scorer, top_n=1)
    assert [c.job_key for c in res.candidates] == ["greenhouse:3"]


def test_scorer_failure_keeps_retrieval_order_and_reports(index):
    class Boom:
        def score(self, pairs):
            raise RuntimeError("model missing")

    original = cands("greenhouse:2", "greenhouse:1")
    res = rerank("q", index, original, Boom())
    assert [c.job_key for c in res.candidates] == ["greenhouse:2", "greenhouse:1"]
    assert res.trace["status"].startswith("failed") and res.trace["reranked"] == 0
    assert all("rerank" not in c.stage_ranks for c in res.candidates)


def test_wrong_score_count_is_treated_as_failure(index):
    class Short:
        def score(self, pairs):
            return [0.1]

    res = rerank("q", index, cands("greenhouse:1", "greenhouse:2"), Short())
    assert res.trace["status"].startswith("failed")


def test_inputs_are_not_mutated(index):
    original = cands("greenhouse:1", "greenhouse:2")
    rerank("q", index, original, FakeScorer(lambda q, p: 1.0 if p.startswith("Backend") else 0.0))
    assert [c.job_key for c in original] == ["greenhouse:1", "greenhouse:2"]
    assert all("rerank" not in c.stage_ranks and "rerank" not in c.channel_scores for c in original)


def test_empty_candidates(index):
    res = rerank("q", index, [], FakeScorer(lambda q, p: 0.0))
    assert res.candidates == [] and res.trace["reranked"] == 0


def test_cross_encoder_scorer_is_lazy_and_handles_empty():
    s = CrossEncoderScorer("does-not-exist")
    assert s.score([]) == []  # must not try to load the model
    assert s._model is None
