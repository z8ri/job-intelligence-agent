import hashlib

import numpy as np
import pytest

from src.agent.embeddings import CachedEmbedder, EmbeddingCache, EmbeddingError
from src.agent.retrieval import JobIndex, tokenize
from src.agent.snapshots import Snapshot

DIM = 256


def _vec(text):
    v = np.zeros(DIM, dtype=np.float32)
    for tok in tokenize(text):
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


class FakeEmbed:
    """Deterministic bag-of-words embedder that records every text it is asked for."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        return np.stack([_vec(t) for t in texts])

    @property
    def texts(self):
        return [t for c in self.calls for t in c]


def embedder(fn=None, cache=None, model="fake-1"):
    return CachedEmbedder(fn or FakeEmbed(), model, cache)


def job(job_id, title, body, url=None, source="greenhouse"):
    return Snapshot.create(
        source=source, source_job_id=job_id, title=title, raw_content=body, url=url,
        fetched_at="2026-03-01T00:00:00+00:00",
    )


LLM_APP = job(
    "1", "Applied AI Engineer",
    "<p>About us.</p><h3>What you'll do</h3><ul><li>Build LLM-powered agents with tool use and retrieval</li></ul>"
    "<h3>What you should have</h3><ul><li>Python</li></ul>",
)
TRAINING = job(
    "2", "ML Research Engineer",
    "<p>About us.</p><h3>What you'll do</h3><ul><li>Pretrain foundation models on GPU clusters</li></ul>"
    "<h3>What you should have</h3><ul><li>Familiarity with LLM applications and agents</li></ul>",
)
BACKEND = job(
    "3", "Backend Engineer",
    "<p>About us.</p><h3>What you'll do</h3><ul><li>Design payment APIs in Go</li></ul>"
    "<h3>What you should have</h3><ul><li>Kubernetes</li></ul>",
)
HN = job("4", "Founding engineer", "Acme | NYC | ONSITE | we build LLM agents for insurance claims", source="hackernews")


def index(snaps, emb="default", **kw):
    return JobIndex(snaps, embedder() if emb == "default" else emb, **kw)


# ---- tokenizer -------------------------------------------------------------

def test_tokenizer_keeps_technical_tokens_and_stems():
    toks = tokenize("Senior C++ and C# developers, Node.js, full-time; building agents")
    assert "c++" in toks and "c#" in toks and "node.js" in toks
    assert "full" in toks and "time" in toks  # hyphen split
    assert "agent" in toks and "build" in toks  # stemmed
    assert "and" not in toks


def test_tokenizer_drops_stray_single_letters_but_keeps_c_and_r():
    toks = tokenize("a b c r x")
    assert toks == ["c", "r"]


def test_tokenizer_ignores_non_ascii_text():
    assert tokenize("纽约 初级") == []
    assert tokenize(None) == []


# ---- embedding cache ---------------------------------------------------------

def test_cache_avoids_reembedding_and_counts_hits():
    fake = FakeEmbed()
    e = embedder(fake)
    a = e.embed(["alpha beta", "gamma"])
    b = e.embed(["gamma", "alpha beta"])
    assert e.stats() == {"hits": 2, "misses": 2}
    assert fake.texts == ["alpha beta", "gamma"]
    np.testing.assert_allclose(a[0], b[1])


def test_duplicate_texts_in_one_call_are_embedded_once_but_returned_in_order():
    fake = FakeEmbed()
    out = embedder(fake).embed(["x y", "z", "x y"])
    assert fake.texts == ["x y", "z"]
    assert out.shape[0] == 3
    np.testing.assert_allclose(out[0], out[2])


def test_cache_is_keyed_by_model():
    cache = EmbeddingCache()
    f1, f2 = FakeEmbed(), FakeEmbed()
    embedder(f1, cache, "m1").embed(["hello world"])
    embedder(f2, cache, "m2").embed(["hello world"])
    assert f1.texts == f2.texts == ["hello world"]  # different model => not shared
    assert cache.count() == 2


def test_cache_persists_across_instances(tmp_path):
    path = tmp_path / "emb.db"
    embedder(FakeEmbed(), EmbeddingCache(path)).embed(["persist me"])
    fake = FakeEmbed()
    embedder(fake, EmbeddingCache(path)).embed(["persist me"])
    assert fake.calls == []


def test_partial_progress_survives_a_failing_batch(monkeypatch):
    import src.agent.embeddings as mod

    monkeypatch.setattr(mod, "_BATCH", 2)
    calls = {"n": 0}
    inner = FakeEmbed()

    def flaky(texts):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("rate limited")
        return inner(texts)

    cache = EmbeddingCache()
    e = embedder(flaky, cache)
    with pytest.raises(EmbeddingError):
        e.embed(["a1", "b2", "c3", "d4", "e5"])
    assert cache.count() == 2  # first batch was kept
    e2 = embedder(inner, cache)
    e2.embed(["a1", "b2", "c3", "d4", "e5"])
    assert e2.stats()["hits"] == 2


def test_wrong_vector_count_is_an_error():
    e = embedder(lambda texts: np.zeros((len(texts) - 1, 4), dtype=np.float32))
    with pytest.raises(EmbeddingError):
        e.embed(["one", "two"])


# ---- retrieval ---------------------------------------------------------------

def test_bm25_only_search_when_no_embedder():
    idx = index([LLM_APP, TRAINING, BACKEND], emb=None)
    res = idx.search("payment APIs in Go")
    assert res.candidates[0].job_key == "greenhouse:3"
    assert res.trace["degraded"] == ["dense_full", "dense_resp"]
    assert set(res.candidates[0].stage_ranks) == {"bm25", "rrf", "final"}


def test_responsibility_channel_prefers_jobs_that_do_the_work():
    idx = index([LLM_APP, TRAINING, BACKEND])
    res = idx.search("build LLM agents with tool use", top_n=5)
    by_key = {c.job_key: c for c in res.candidates}
    # both mention LLM agents, but only LLM_APP does it in its responsibilities
    assert by_key["greenhouse:1"].stage_ranks["dense_resp"] < by_key["greenhouse:2"].stage_ranks["dense_resp"]
    assert res.candidates[0].job_key == "greenhouse:1"


def test_responsibility_channel_only_indexes_jobs_with_that_section():
    idx = index([LLM_APP, HN])
    res = idx.search("LLM agents")
    by_key = {c.job_key: c for c in res.candidates}
    assert "dense_resp" not in by_key["hackernews:4"].stage_ranks  # free-form post: no such section
    assert "dense_full" in by_key["hackernews:4"].stage_ranks  # but the full-text channel still sees it


def test_best_segment_span_points_into_normalized_text():
    idx = index([LLM_APP, BACKEND])
    cand = next(c for c in idx.search("LLM agents tool use").candidates if c.job_key == "greenhouse:1")
    start, end = cand.best_segment
    assert "LLM-powered agents" in LLM_APP.text[start:end]


def test_stage_ranks_and_channel_scores_are_recorded():
    idx = index([LLM_APP, TRAINING, BACKEND])
    res = idx.search("LLM agents")
    top = res.candidates[0]
    assert top.stage_ranks["rrf"] == 1 and top.stage_ranks["final"] == 1
    assert {"bm25", "dense_full"} <= set(top.stage_ranks)
    assert set(top.channel_scores) == set(top.stage_ranks) - {"rrf", "final"}
    assert res.trace["channels"]["dense_resp"]["status"] == "ok"


def test_final_ranks_are_contiguous_and_scores_descend():
    idx = index([LLM_APP, TRAINING, BACKEND, HN])
    res = idx.search("LLM agents")
    assert [c.stage_ranks["final"] for c in res.candidates] == list(range(1, len(res.candidates) + 1))
    scores = [c.score for c in res.candidates]
    assert scores == sorted(scores, reverse=True)


def test_top_n_limits_results():
    idx = index([LLM_APP, TRAINING, BACKEND, HN])
    assert len(idx.search("LLM agents", top_n=2).candidates) == 2


def test_search_is_deterministic():
    snaps = [LLM_APP, TRAINING, BACKEND, HN]
    a = [c.job_key for c in index(snaps).search("LLM agents").candidates]
    b = [c.job_key for c in index(list(reversed(snaps))).search("LLM agents").candidates]
    assert a == b


def test_dedupe_merges_only_identical_links():
    a = job("10", "Applied AI Engineer", LLM_APP.raw_content, url="https://x.com/j/1")
    b = job("11", "Applied AI Engineer", LLM_APP.raw_content, url="https://X.com/j/1/", source="lever")
    c = job("12", "Applied AI Engineer", LLM_APP.raw_content)  # same title/text, no link
    res = index([a, b, c]).search("LLM agents tool use")
    keys = [x.job_key for x in res.candidates]
    assert len(keys) == 2  # a/b merged, c kept
    merged = next(x for x in res.candidates if x.merged_keys)
    assert len(merged.merged_keys) == 1
    assert res.trace["deduped"] == 1


def test_embedding_failure_degrades_to_bm25_with_trace():
    def boom(texts):
        raise RuntimeError("no network")

    idx = index([LLM_APP, TRAINING, BACKEND], emb=embedder(boom))
    res = idx.search("payment APIs in Go")
    assert res.candidates[0].job_key == "greenhouse:3"
    assert res.trace["degraded"] == ["dense_full", "dense_resp"]
    assert "failed" in res.trace["channels"]["dense_full"]["status"]


def test_index_recovers_after_transient_embedding_failure():
    inner = FakeEmbed()
    state = {"fail": True}

    def flaky(texts):
        if state["fail"]:
            raise RuntimeError("blip")
        return inner(texts)

    idx = index([LLM_APP, TRAINING, BACKEND], emb=embedder(flaky))
    assert idx.search("LLM agents").trace["degraded"]
    state["fail"] = False
    assert idx.search("LLM agents").trace["degraded"] == []


def test_second_search_reuses_cache_for_documents():
    fake = FakeEmbed()
    idx = index([LLM_APP, TRAINING, BACKEND], emb=embedder(fake))
    idx.search("LLM agents")
    doc_calls = len(fake.texts)
    res = idx.search("payment APIs")
    assert len(fake.texts) == doc_calls + 1  # only the new query is embedded
    assert res.trace["embedding"]["misses"] == 1


def test_query_with_no_lexical_overlap_still_finds_by_dense_only():
    idx = index([LLM_APP, BACKEND])
    res = idx.search("zzzz qqqq")
    assert res.trace["channels"]["bm25"]["recalled"] == 0
    assert res.candidates  # dense channels still return something


def test_empty_index_returns_no_candidates():
    res = index([]).search("anything")
    assert res.candidates == []


def test_long_text_is_truncated_for_full_text_channel():
    fake = FakeEmbed()
    long_job = job("9", "Long", "word " * 5000)
    index([long_job], emb=embedder(fake), full_text_chars=100).search("word")
    assert all(len(t) <= 100 + len("Long\n") for t in fake.texts[:1])
