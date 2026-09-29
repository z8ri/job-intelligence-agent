import json
import re
import threading
import time

import pytest

from src.agent.models import Condition, ConditionSet, RegionsValue, TextValue
from src.agent.retrieval import Candidate
from src.agent.snapshots import Snapshot
from src.agent.verification import Budget, JudgmentCache, SingleFlight, Verifier

QUERY = "想找纽约的 LLM 应用开发岗位"
REGION = Condition(field="work_region", strength="hard", quote="纽约", value=RegionsValue(regions=["New York"]))
FOCUS = Condition(field="role_focus", strength="soft", quote="LLM 应用开发", value=TextValue(text="LLM application development"))
SKILL = Condition(field="skill", strength="soft", quote="LLM", value=TextValue(text="python"))


def cs(*conds, version=1):
    return ConditionSet(raw_query=QUERY, conditions=list(conds), version=version)


def make_job(i, city):
    return Snapshot.create(
        source="greenhouse", source_job_id=str(i), title=f"Engineer {i}",
        raw_content=f"Located in {city}. Build LLM applications.", fetched_at="2026-03-01T00:00:00+00:00",
    )


class FakeLLM:
    """Rule-based judge: region conflicts when the posting says London; role_focus is supported."""

    def __init__(self, delay=0.0, fail_titles=(), fail_all=False):
        self.delay = delay
        self.fail_titles = set(fail_titles)
        self.fail_all = fail_all
        self.calls: list[tuple[str, list[str]]] = []
        self._lock = threading.Lock()

    def __call__(self, system, user):
        title = re.search(r"Title: (.*)", user).group(1)
        ids = re.findall(r'"condition_id": "([^"]+)"', user)
        with self._lock:
            self.calls.append((title, ids))
        if self.delay:
            time.sleep(self.delay)
        if self.fail_all or title in self.fail_titles:
            raise RuntimeError("upstream 500")
        text = re.search(r"<job>(.*)</job>", user, re.S).group(1)
        out = []
        for cid in ids:
            if cid.startswith("work_region"):
                if "London" in text:
                    out.append({"condition_id": cid, "verdict": "conflict", "quote": "Located in London.", "reason": "uk"})
                else:
                    out.append({"condition_id": cid, "verdict": "support", "quote": "Located in New York.", "reason": "ny"})
            elif cid.startswith("role_focus"):
                out.append({"condition_id": cid, "verdict": "support", "quote": "Build LLM applications.", "reason": "ok"})
            else:
                out.append({"condition_id": cid, "verdict": "unknown", "quote": None, "reason": ""})
        return json.dumps({"judgments": out})


def setup(cities, **verifier_kw):
    snaps = {f"greenhouse:{i}": make_job(i, c) for i, c in enumerate(cities)}
    cands = [Candidate(job_key=k, score=1.0, stage_ranks={"final": n}) for n, k in enumerate(snaps, start=1)]
    llm = verifier_kw.pop("llm", None) or FakeLLM()
    cache = verifier_kw.pop("cache", None) or JudgmentCache()
    return snaps, cands, llm, cache, Verifier(cache, complete=llm, model="m", **verifier_kw)


def keys(vjs):
    return [v.candidate.job_key for v in vjs]


def test_checks_in_rank_order_and_stops_at_target():
    snaps, cands, llm, cache, v = setup(["New York", "London", "New York", "New York", "New York", "New York"])
    res = v.verify(cands, snaps.__getitem__, cs(REGION, FOCUS), Budget(target_kept=3))
    assert keys(res.kept) == ["greenhouse:0", "greenhouse:2", "greenhouse:3"]
    assert keys(res.excluded) == ["greenhouse:1"]
    assert {u.note for u in res.unverified} == {"not checked"} and len(res.unverified) == 2
    assert len(llm.calls) == 4  # never looked at jobs 4 and 5
    assert res.status == "complete" and res.reasons == []


def test_excluded_job_carries_verified_evidence():
    snaps, cands, *_, v = setup(["London", "New York"])
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=5))
    ex = res.excluded[0]
    assert ex.conflicts[0].quote == "Located in London." and ex.conflicts[0].span is not None
    assert snaps[ex.candidate.job_key].text[slice(*ex.conflicts[0].span)] == "Located in London."


def test_fewer_candidates_than_target_is_still_complete():
    snaps, cands, llm, cache, v = setup(["New York", "London"])
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=10))
    assert res.status == "complete" and len(res.kept) == 1 and len(res.excluded) == 1


def test_second_run_is_served_from_cache():
    snaps, cands, llm, cache, v = setup(["New York", "London", "New York"])
    v.verify(cands, snaps.__getitem__, cs(REGION, FOCUS), Budget(target_kept=5))
    n = len(llm.calls)
    res = v.verify(cands, snaps.__getitem__, cs(REGION, FOCUS), Budget(target_kept=5))
    assert len(llm.calls) == n
    assert res.stats["llm_calls"] == 0 and res.stats["cache_hits"] == 6
    assert len(res.kept) == 2 and len(res.excluded) == 1


def test_flipping_strength_reuses_cache_but_changes_outcome():
    snaps, cands, llm, cache, v = setup(["New York", "London"])
    v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=5))
    n = len(llm.calls)
    soft_region = Condition(field="work_region", strength="soft", quote="纽约", value=REGION.value)
    res = v.verify(cands, snaps.__getitem__, cs(soft_region, version=2), Budget(target_kept=5))
    assert len(llm.calls) == n  # same condition value: no new calls
    assert len(res.kept) == 2 and res.excluded == []  # a soft conflict no longer excludes
    assert res.kept[0].judgment.condition_version == 2  # result is bound to the new version


def test_added_condition_only_sends_the_missing_id():
    snaps, cands, llm, cache, v = setup(["New York"])
    v.verify(cands, snaps.__getitem__, cs(REGION), Budget())
    v.verify(cands, snaps.__getitem__, cs(REGION, FOCUS, version=2), Budget())
    assert llm.calls[-1][1] == [FOCUS.id]


def test_changed_job_text_is_rejudged():
    snaps, cands, llm, cache, v = setup(["New York"])
    v.verify(cands, snaps.__getitem__, cs(REGION), Budget())
    changed = Snapshot.create(
        source="greenhouse", source_job_id="0", title="Engineer 0",
        raw_content="Located in London. Build LLM applications.", fetched_at="2026-04-01T00:00:00+00:00",
    )
    res = v.verify(cands, {"greenhouse:0": changed}.__getitem__, cs(REGION), Budget())
    assert len(llm.calls) == 2
    assert len(res.excluded) == 1


def test_llm_call_budget_yields_partial_with_reason():
    snaps, cands, llm, cache, v = setup(["New York"] * 6)
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=6, max_llm_calls=2))
    assert len(llm.calls) == 2 and len(res.kept) == 2
    assert res.status == "partial" and "llm call budget exhausted" in res.reasons
    assert len(res.unverified) == 4


def test_cache_hits_do_not_consume_call_budget():
    snaps, cands, llm, cache, v = setup(["New York"] * 4)
    v.verify(cands[:2], snaps.__getitem__, cs(REGION), Budget(target_kept=2))
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=4, max_llm_calls=2))
    assert len(res.kept) == 4 and res.status == "complete"


def test_max_candidates_caps_the_search():
    snaps, cands, llm, cache, v = setup(["London"] * 5 + ["New York"])
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=1, max_candidates=3))
    assert res.kept == [] and len(res.excluded) == 3
    assert res.status == "partial" and "max_candidates reached" in res.reasons


def test_failures_are_reported_and_not_cached():
    llm = FakeLLM(fail_titles={"Engineer 1"})
    snaps, cands, _, cache, v = setup(["New York", "New York", "New York"], llm=llm)
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=5))
    assert keys(res.kept) == ["greenhouse:0", "greenhouse:2"]
    assert res.stats["failures"] == 1
    bad = next(u for u in res.unverified if u.candidate.job_key == "greenhouse:1")
    assert bad.status == "unverified" and "judge failed" in bad.note
    assert cache.count() == 2  # the failed job left nothing behind


def test_consecutive_failures_stop_the_search():
    llm = FakeLLM(fail_all=True)
    snaps, cands, _, cache, v = setup(["New York"] * 8, llm=llm)
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=8, max_consecutive_failures=3, max_workers=1))
    assert res.status == "partial" and "too many consecutive failures" in res.reasons
    assert len(llm.calls) < 8
    assert res.kept == []


def test_deadline_returns_partial_and_marks_timeout():
    llm = FakeLLM(delay=0.6)
    snaps, cands, _, cache, v = setup(["New York", "New York"], llm=llm)
    t = time.monotonic()
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget(target_kept=2, deadline_s=0.15))
    assert time.monotonic() - t < 0.5
    assert res.status == "partial" and "deadline reached" in res.reasons
    assert all(u.note in ("timed out", "not checked") for u in res.unverified)


def test_unknown_hard_condition_is_kept_but_flagged():
    llm = FakeLLM()
    snaps, cands, _, cache, v = setup(["New York"], llm=llm)
    res = v.verify(cands, snaps.__getitem__, cs(Condition(field="skill", strength="hard", quote="LLM", value=SKILL.value)), Budget())
    assert len(res.kept) == 1 and res.kept[0].unconfirmed_hard == [SKILL.id]


def test_downgraded_answers_are_not_cached():
    def liar(system, user):
        ids = re.findall(r'"condition_id": "([^"]+)"', user)
        return json.dumps({"judgments": [{"condition_id": i, "verdict": "conflict", "quote": "made up", "reason": ""} for i in ids]})

    cache = JudgmentCache()
    snaps, cands, *_ = setup(["New York"])
    v = Verifier(cache, complete=liar, model="m")
    res = v.verify(cands, snaps.__getitem__, cs(REGION), Budget())
    assert len(res.kept) == 1 and res.excluded == []  # unverifiable conflict cannot exclude
    assert cache.count() == 0


def test_cache_is_scoped_by_model_and_prompt_version():
    snaps, cands, llm, cache, v = setup(["New York"])
    v.verify(cands, snaps.__getitem__, cs(REGION), Budget())
    Verifier(cache, complete=llm, model="other").verify(cands, snaps.__getitem__, cs(REGION), Budget())
    Verifier(cache, complete=llm, model="m", prompt_version="other").verify(cands, snaps.__getitem__, cs(REGION), Budget())
    assert len(llm.calls) == 3


def test_cache_persists_on_disk(tmp_path):
    path = tmp_path / "j.db"
    snaps, cands, llm, cache, v = setup(["New York"], cache=JudgmentCache(path))
    v.verify(cands, snaps.__getitem__, cs(REGION), Budget())
    cache.close()
    llm2 = FakeLLM()
    v2 = Verifier(JudgmentCache(path), complete=llm2, model="m")
    v2.verify(cands, snaps.__getitem__, cs(REGION), Budget())
    assert llm2.calls == []


def test_singleflight_shares_one_execution_and_propagates_errors():
    flight = SingleFlight()
    runs = []
    gate = threading.Event()

    def slow():
        runs.append(1)
        gate.wait(1)
        return "value"

    results = []
    threads = [threading.Thread(target=lambda: results.append(flight.do("k", slow))) for _ in range(4)]
    [t.start() for t in threads]
    time.sleep(0.1)
    gate.set()
    [t.join() for t in threads]
    assert len(runs) == 1
    assert sorted(leader for _, leader in results) == [False, False, False, True]

    def boom():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        flight.do("k2", boom)
    assert flight.do("k2", lambda: 1)[0] == 1  # key is released after failure


def test_concurrent_requests_for_the_same_job_share_one_llm_call():
    llm = FakeLLM(delay=0.3)
    cache = JudgmentCache()
    flight = SingleFlight()
    snaps = {"greenhouse:0": make_job(0, "New York")}
    cands = [Candidate(job_key="greenhouse:0", score=1.0)]
    results = []

    def run():
        v = Verifier(cache, complete=llm, model="m", flight=flight)
        results.append(v.verify(cands, snaps.__getitem__, cs(REGION), Budget()))

    t1 = threading.Thread(target=run)
    t2 = threading.Thread(target=run)
    t1.start()
    time.sleep(0.1)
    t2.start()
    t1.join()
    t2.join()
    assert len(llm.calls) == 1
    assert all(len(r.kept) == 1 for r in results)
    assert sum(r.stats["shared_calls"] for r in results) == 1
