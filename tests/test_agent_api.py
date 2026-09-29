import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from src.agent.api import create_app
from src.agent.conditions import ConditionParseError
from src.agent.models import Clarification, Condition, ConditionSet, RegionsValue, TextValue
from src.agent.retrieval import JobIndex
from src.agent.service import SearchService
from src.agent.snapshots import Snapshot
from src.agent.tasks import TaskStore
from src.agent.verification import Budget, JudgmentCache, Verifier
from tests.test_agent_verification import FakeLLM

QUERY = "想找纽约的 LLM 应用开发岗位"
REGION = Condition(field="work_region", strength="hard", quote="纽约", value=RegionsValue(regions=["New York"]))
FOCUS = Condition(field="role_focus", strength="hard", quote="LLM 应用开发", value=TextValue(text="LLM applications"))


def make_snaps(cities):
    return [
        Snapshot.create(source="greenhouse", source_job_id=str(i), title=f"Engineer {i}",
                        raw_content=f"Located in {c}. Build LLM applications.", fetched_at="2026-03-01T00:00:00+00:00")
        for i, c in enumerate(cities)
    ] + [
        Snapshot.create(source="greenhouse", source_job_id="x1", title="Cook", raw_content="Cook meals daily.",
                        fetched_at="2026-03-01T00:00:00+00:00"),
        Snapshot.create(source="greenhouse", source_job_id="x2", title="Driver", raw_content="Drive trucks.",
                        fetched_at="2026-03-01T00:00:00+00:00"),
    ]


class ReverseScorer:
    def score(self, pairs):
        return [float(i) for i in range(len(pairs))]  # later candidates score higher


class BrokenScorer:
    def score(self, pairs):
        raise RuntimeError("model missing")


def build(cities=("New York", "London", "New York"), *, conditions=None, scorer=None, llm=None, budget=None, parse=None):
    cs = conditions or ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    llm = llm or FakeLLM()
    service = SearchService(
        JobIndex(make_snaps(cities)), scorer, Verifier(JudgmentCache(), complete=llm, model="m"), TaskStore(),
        parse=parse or (lambda q: cs), budget=budget or Budget(target_kept=5),
    )
    return service, TestClient(create_app(service)), llm


def post(client, path, body):
    return client.post(path, json=body)


def test_search_returns_kept_excluded_with_evidence_and_bound_version():
    _, client, _ = build()
    r = post(client, "/search", {"query": QUERY})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "complete" and body["condition_version"] == 1
    kept = {j["job_key"] for j in body["kept"]}
    assert kept == {"greenhouse:0", "greenhouse:2"}
    ex = body["excluded"][0]
    assert ex["job_key"] == "greenhouse:1" and ex["evidence"][0]["quote"] == "Located in London."
    assert body["conditions"]["version"] == 1 and set(body["trace"]["timings_s"]) == {"retrieval", "rerank", "verification", "total"}
    assert body["kept"][0]["rank"] is not None and "bm25" in body["kept"][0]["stage_ranks"]


def test_get_task_and_job_endpoints():
    _, client, _ = build()
    task_id = post(client, "/search", {"query": QUERY}).json()["task_id"]
    got = client.get(f"/tasks/{task_id}").json()
    assert got["status"] == "complete" and got["versions"] == [1]
    assert client.get("/tasks/nope").status_code == 404
    job = client.get("/jobs/greenhouse:0").json()
    assert job["title"] == "Engineer 0" and "Build LLM" in job["text"]
    assert client.get("/jobs/greenhouse:missing").status_code == 404
    assert client.get("/health").json() == {"ok": True, "jobs": 5}


def test_clarify_state_searches_nothing_until_confirmed():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION],
                      clarifications=[Clarification(question="Is hybrid ok?", options=["yes", "no"])])
    service, client, llm = build(conditions=cs)
    body = post(client, "/search", {"query": QUERY}).json()
    assert body["status"] == "clarify" and body["clarifications"][0]["question"] == "Is hybrid ok?"
    assert body["kept"] == [] and llm.calls == []
    run = post(client, f"/tasks/{body['task_id']}/run", {"expected_version": 1}).json()
    assert run["status"] == "complete" and len(run["kept"]) == 2
    again = post(client, f"/tasks/{body['task_id']}/run", {"expected_version": 1}).json()
    assert again["status"] == "complete"


def test_proceed_flag_skips_clarification():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION], clarifications=[Clarification(question="q?")])
    _, client, _ = build(conditions=cs)
    assert post(client, "/search", {"query": QUERY, "proceed": True}).json()["status"] == "complete"


def test_unparseable_request_is_failed_with_503():
    def bad(_):
        raise ConditionParseError("no conditions extracted")

    _, client, _ = build(parse=bad)
    r = post(client, "/search", {"query": QUERY})
    assert r.status_code == 503 and r.json()["status"] == "failed" and "no conditions" in r.json()["reasons"][0]
    assert client.get(f"/tasks/{r.json()['task_id']}").json()["status"] == "failed"


def test_empty_index_is_failed():
    service, client, _ = build()
    service.index = JobIndex([])
    r = post(client, "/search", {"query": QUERY})
    assert r.status_code == 503 and r.json()["reasons"] == ["job index is empty"]


def test_validation_error_for_empty_query():
    _, client, _ = build()
    assert post(client, "/search", {"query": ""}).status_code == 422


def test_revise_flips_strength_reuses_cache_and_keeps_old_version():
    _, client, llm = build()
    first = post(client, "/search", {"query": QUERY}).json()
    calls = len(llm.calls)
    tid = first["task_id"]
    r = post(client, f"/tasks/{tid}/revise", {"expected_version": 1, "strengths": {REGION.id: "soft"}})
    body = r.json()
    assert r.status_code == 200 and body["condition_version"] == 2 and body["changes"]["modified"] == [REGION.id]
    assert len(llm.calls) == calls  # cache reused
    assert {j["job_key"] for j in body["kept"]} == {"greenhouse:0", "greenhouse:1", "greenhouse:2"}
    assert body["excluded"] == []
    assert client.get(f"/tasks/{tid}?version=1").json()["condition_version"] == 1  # old result intact
    assert client.get(f"/tasks/{tid}").json()["condition_version"] == 2
    assert client.get(f"/tasks/{tid}").json()["versions"] == [1, 2]


def test_stale_version_is_rejected_with_409():
    _, client, _ = build()
    tid = post(client, "/search", {"query": QUERY}).json()["task_id"]
    post(client, f"/tasks/{tid}/revise", {"expected_version": 1, "remove": [REGION.id]})
    r = post(client, f"/tasks/{tid}/revise", {"expected_version": 1, "strengths": {FOCUS.id: "soft"}})
    assert r.status_code == 409
    assert r.json()["detail"] == {"error": "version_conflict", "current_version": 2, "expected_version": 1}
    assert post(client, f"/tasks/{tid}/run", {"expected_version": 1}).status_code == 409


def test_revision_without_effective_change_creates_no_new_version():
    _, client, _ = build()
    tid = post(client, "/search", {"query": QUERY}).json()["task_id"]
    body = post(client, f"/tasks/{tid}/revise", {"expected_version": 1, "strengths": {REGION.id: "hard"}}).json()
    assert body["condition_version"] == 1 and body["versions"] == [1]


@pytest.mark.parametrize("payload", [
    {"strengths": {"skill:00000000": "hard"}},
    {"remove": ["skill:00000000"]},
    {"strengths": {REGION.id: "maybe"}},
    {"remove": [REGION.id, FOCUS.id]},
])
def test_invalid_revisions_are_422(payload):
    _, client, _ = build()
    tid = post(client, "/search", {"query": QUERY}).json()["task_id"]
    r = post(client, f"/tasks/{tid}/revise", {"expected_version": 1, **payload})
    assert r.status_code == 422 and r.json()["detail"]["error"] == "invalid_revision"


def test_budget_exhaustion_is_partial_and_reports_unverified():
    _, client, _ = build(cities=["New York"] * 6, budget=Budget(target_kept=6, max_llm_calls=2))
    body = post(client, "/search", {"query": QUERY}).json()
    assert body["status"] == "partial" and "llm call budget exhausted" in body["reasons"]
    assert len(body["kept"]) == 2 and body["unverified"]


def test_reranker_failure_degrades_to_partial_with_reason():
    _, client, _ = build(scorer=BrokenScorer())
    body = post(client, "/search", {"query": QUERY}).json()
    assert body["status"] == "partial" and "reranker unavailable, kept retrieval order" in body["reasons"]
    assert len(body["kept"]) == 2  # results still returned


def test_reranker_order_is_reflected_in_ranks():
    _, client, _ = build(cities=["New York"] * 3, scorer=ReverseScorer())
    body = post(client, "/search", {"query": QUERY}).json()
    assert body["status"] == "complete"
    assert [j["rank"] for j in body["kept"]] == [1, 2, 3]
    assert all("rerank" in j["stage_ranks"] for j in body["kept"])


def test_identical_concurrent_searches_share_one_computation():
    llm = FakeLLM(delay=0.3)
    service, client, _ = build(cities=["New York"] * 3, llm=llm)
    out = []
    threads = [threading.Thread(target=lambda: out.append(client.post("/search", json={"query": QUERY}).json())) for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len({o["task_id"] for o in out}) == 3  # separate task records
    assert all(o["status"] == "complete" and len(o["kept"]) == 3 for o in out)
    assert len(llm.calls) == 3  # one judgement per job, not per request


class CountingScorer:
    def __init__(self):
        self.calls = 0

    def score(self, pairs):
        self.calls += 1
        return [float(-i) for i in range(len(pairs))]


def test_revision_with_same_retrieval_text_reuses_retrieval_and_rerank():
    scorer = CountingScorer()
    _, client, _ = build(scorer=scorer)
    tid = post(client, "/search", {"query": QUERY}).json()["task_id"]
    assert scorer.calls == 1
    post(client, f"/tasks/{tid}/revise", {"expected_version": 1, "strengths": {REGION.id: "soft"}})
    assert scorer.calls == 1  # region does not change what is retrieved


def test_revision_that_changes_retrieval_text_reranks_again():
    scorer = CountingScorer()
    _, client, _ = build(scorer=scorer)
    tid = post(client, "/search", {"query": QUERY}).json()["task_id"]
    post(client, f"/tasks/{tid}/revise", {"expected_version": 1, "remove": [FOCUS.id]})
    assert scorer.calls == 2
