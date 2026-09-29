import json
import re

import pytest
from fastapi.testclient import TestClient

from src.agent.api import create_app
from src.agent.evidence import JobJudgment, Judgment
from src.agent.explain import explain_rank_changes
from src.agent.fit import mode_fit, region_fit, salary_fit
from src.agent.models import (
    Condition, ConditionSet, ModesValue, RegionsValue, SalaryValue, TextValue,
)
from src.agent.planning import DEFERRED_NOTE, plan_verification
from src.agent.retrieval import Candidate, JobIndex
from src.agent.scoring import condition_score, soft_breakdown, soft_score, to_confirm
from src.agent.service import InvalidRevision, SearchService
from src.agent.snapshots import Snapshot
from src.agent.tasks import TaskStore
from src.agent.verification import Budget, JudgmentCache, Verifier
from tests.test_agent_verification import FakeLLM

QUERY = "想找纽约的 LLM 应用开发岗位，年薪至少 150000 美元，最好能远程"
REGION = Condition(field="work_region", strength="hard", quote="纽约", value=RegionsValue(regions=["New York"]))
FOCUS = Condition(field="role_focus", strength="hard", quote="LLM 应用开发", value=TextValue(text="LLM applications"))
SALARY = Condition(field="salary", strength="soft", quote="年薪至少 150000 美元", weight=0.8,
                   value=SalaryValue(min_amount=150000, currency="USD", period="year"))
REMOTE = Condition(field="remote_mode", strength="soft", quote="最好能远程", weight=0.4, value=ModesValue(modes=["remote"]))


def snap(i, *, location="New York", body="Build LLM applications.", title=None, **hints):
    return Snapshot.create(source="greenhouse", source_job_id=str(i), title=title or f"Eng {i}", location=location,
                           raw_content=f"Located in {location}. {body}", fetched_at="2026-03-01T00:00:00+00:00",
                           hints=hints)


def judgment(cs, **verdicts):
    return JobJudgment(job_key="k", content_hash="h", condition_version=1, judgments={
        c.id: Judgment(condition_id=c.id, verdict=verdicts.get(c.field, "unknown"), reason="r") for c in cs.conditions})


# ---- structured fit ---------------------------------------------------------------------------

def test_salary_fit_grades_shortfall_and_ignores_unusable_data():
    v = SalaryValue(min_amount=150000)
    assert salary_fit(v, {"salary_min": 160000, "salary_max": 200000}).score == 1.0
    near, far = salary_fit(v, {"salary_min": 140000}).score, salary_fit(v, {"salary_min": 100000, "salary_max": 110000}).score
    assert 0.5 < near < 1.0 and far < 0.2
    assert salary_fit(v, {"salary_min": 1000}) is None          # hourly/monthly scrape, not a yearly figure
    assert salary_fit(v, {}) is None
    assert salary_fit(SalaryValue(min_amount=150000, currency="EUR"), {"salary_min": 200000}) is None
    monthly = SalaryValue(min_amount=10000, period="month")     # 120k a year
    assert salary_fit(monthly, {"salary_min": 130000}).score == 1.0


def test_region_fit_handles_state_suffix_multi_location_and_country_wide():
    ny = RegionsValue(regions=["New York"])
    assert region_fit(ny, "New York, NY").score == 1.0
    assert region_fit(ny, "San Francisco, CA • New York, NY • United States").score == 1.0
    assert region_fit(ny, "Remote").score == 0.9
    assert region_fit(ny, "San Francisco").score < 0.2
    assert region_fit(ny, "Unknown") is None and region_fit(ny, "") is None
    assert region_fit(RegionsValue(regions=["United States"]), "Austin, TX").score == 1.0


def test_mode_fit_uses_adjacency_and_needs_a_label():
    v = ModesValue(modes=["remote"])
    assert mode_fit(v, {"remote": "remote"}).score == 1.0
    assert 0 < mode_fit(v, {"remote": "hybrid"}).score < 1.0
    assert mode_fit(v, {}) is None


# ---- scoring rule: evidence first, structure fills gaps -----------------------------------------

def test_condition_score_rule():
    good, bad = snap(1, salary_min=180000), snap(2, salary_min=140000)
    assert condition_score(SALARY, "support", bad)["score"] == 1.0            # verified evidence wins
    near_miss = condition_score(SALARY, "conflict", bad)
    assert near_miss["score"] == 0.25 and near_miss["source"] == "evidence+structured"
    assert condition_score(SALARY, "conflict", snap(3))["score"] == 0.0       # no structured data: plain conflict
    unk = condition_score(SALARY, "unknown", good)
    assert unk["score"] == 1.0 and unk["source"] == "structured" and "listed pay" in unk["fit_basis"]
    assert condition_score(SALARY, "unknown", snap(4))["score"] == 0.5


def test_breakdown_reports_source_and_weights():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, SALARY, REMOTE])
    bd = soft_breakdown(cs, judgment(cs), snap(1, salary_min=180000, remote="hybrid"))
    assert {b["field"]: b["source"] for b in bd} == {"salary": "structured", "remote_mode": "structured"}
    assert soft_score(bd) == round((0.8 * 1.0 + 0.4 * bd[1]["score"]) / 1.2, 4)


def test_to_confirm_lists_unknown_hard_conditions_with_next_step():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION, SALARY])
    jj = judgment(cs, role_focus="support")
    out = to_confirm(cs, jj, snap(1))
    assert [o["field"] for o in out] == ["work_region"] and "confirm with the employer" in out[0]["next_step"]
    assert to_confirm(cs, judgment(cs, role_focus="support", work_region="support"), snap(1)) == []
    linked = Snapshot.create(source="s", source_job_id="1", raw_content="x", url="https://e.com/j", fetched_at="2026-03-01T00:00:00+00:00")
    assert to_confirm(cs, jj, linked)[0]["next_step"] == "check the posting link"


# ---- verification planning ----------------------------------------------------------------------

def test_hint_contradicting_a_hard_condition_is_deferred_not_dropped():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    snaps = {"greenhouse:1": snap(1, location="Austin, TX"), "greenhouse:2": snap(2), "greenhouse:3": snap(3, location="Remote"),
             "greenhouse:4": snap(4, location="Unknown")}
    cands = [Candidate(job_key=k, score=1.0, stage_ranks={"final": n}) for n, k in enumerate(snaps, 1)]
    ordered, trace = plan_verification(cands, snaps.__getitem__, cs)
    assert [c.job_key for c in ordered] == ["greenhouse:2", "greenhouse:3", "greenhouse:4", "greenhouse:1"]
    assert len(ordered) == len(cands) and trace["deferred_count"] == 1
    assert trace["deferred"][0]["conflicting_hints"][0]["condition_id"] == REGION.id


def test_soft_conditions_never_defer():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, SALARY])
    snaps = {"greenhouse:1": snap(1, salary_min=90000), "greenhouse:2": snap(2)}
    cands = [Candidate(job_key=k, score=1.0, stage_ranks={}) for k in snaps]
    assert [c.job_key for c in plan_verification(cands, snaps.__getitem__, cs)[0]] == list(snaps)


def fillers():
    return [Snapshot.create(source="greenhouse", source_job_id=f"x{i}", title=t, raw_content=b, fetched_at="2026-03-01T00:00:00+00:00")
            for i, (t, b) in enumerate([("Cook", "Cook meals daily."), ("Driver", "Drive trucks."),
                                        ("Nurse", "Care for patients."), ("Welder", "Weld steel beams.")])]


def make_service(snaps, cs, *, budget=None, llm=None):
    llm = llm or FakeLLM()
    service = SearchService(JobIndex(snaps + fillers()), None, Verifier(JudgmentCache(), complete=llm, model="m"), TaskStore(),
                            parse=lambda q: cs, budget=budget or Budget(target_kept=5))
    return service, llm


def test_deferred_candidate_costs_no_call_when_the_list_fills_first():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    service, llm = make_service([snap(1, location="Austin, TX"), snap(2)], cs, budget=Budget(target_kept=1))
    body = service.start(QUERY)
    assert [j["title"] for j in body["kept"]] == ["Eng 2"] and len(llm.calls) == 1
    assert body["unverified"][0]["title"] == "Eng 1" and body["unverified"][0]["note"] == DEFERRED_NOTE
    assert body["trace"]["verification_plan"]["deferred_count"] == 1


def test_deferred_candidate_is_still_verified_when_room_remains():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    body, llm = (lambda s: (s[0].start(QUERY), s[1]))(make_service([snap(1, location="Austin, TX"), snap(2)], cs))
    assert {j["title"] for j in body["kept"]} == {"Eng 1", "Eng 2"}  # the LLM (not the hint) decides
    assert len(llm.calls) == 2


# ---- ranking: confirmed first, structured grade orders unknowns ---------------------------------

def test_unconfirmed_hard_jobs_rank_below_confirmed_ones():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION, REMOTE])
    # Eng 1 says nothing about location (region unknown) but is fully remote; Eng 2 confirms New York but is onsite
    service, _ = make_service([snap(1, location="", body="Build LLM applications.", remote="remote"),
                               snap(2, body="Build LLM applications.", remote="onsite")], cs)
    kept = service.start(QUERY)["kept"]
    assert [(j["title"], j["confirmation"]) for j in kept] == [("Eng 2", "confirmed"), ("Eng 1", "needs_confirmation")]
    assert kept[1]["to_confirm"][0]["field"] == "work_region"
    assert kept[1]["soft_score"] > kept[0]["soft_score"]


def test_structured_salary_orders_jobs_whose_evidence_is_silent():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION, SALARY])
    service, _ = make_service([snap(1, salary_min=100000), snap(2, salary_min=190000), snap(3)], cs)
    kept = service.start(QUERY)["kept"]
    assert [j["title"] for j in kept] == ["Eng 2", "Eng 3", "Eng 1"]  # graded above unknown (0.5) above a big shortfall
    assert kept[0]["soft_breakdown"][0]["source"] == "structured"


# ---- rank-change explanation --------------------------------------------------------------------

def job(key, rank, breakdown, **extra):
    return {"job_key": key, "title": key, "rank": rank, "soft_breakdown": breakdown,
            "soft_score": soft_score(breakdown), **extra}


def row(cid, weight, score, field="skill"):
    return {"condition_id": cid, "field": field, "weight": weight, "score": score, "verdict": "support"}


def conds(**weights):
    return {"condition_version": 1, "conditions": {"conditions": [
        {"id": cid, "field": "skill", "strength": "soft", "weight": w, "quote": cid.upper()} for cid, w in weights.items()]}}


def test_contribution_deltas_add_up_to_the_score_change():
    prev = {**conds(py=0.5, rust=0.5), "kept": [job("a", 1, [row("py", 0.5, 1.0), row("rust", 0.5, 0.0)]),
                                                job("b", 2, [row("py", 0.5, 0.0), row("rust", 0.5, 1.0)])],
            "excluded": [], "unverified": []}
    cur = {**conds(py=0.2, rust=0.8), "condition_version": 2,
           "kept": [job("b", 1, [row("py", 0.2, 0.0), row("rust", 0.8, 1.0)]), job("a", 2, [row("py", 0.2, 1.0), row("rust", 0.8, 0.0)])],
           "excluded": [], "unverified": []}
    out = explain_rank_changes(prev, cur)
    assert out["summary"]["up"] == 1 and out["summary"]["down"] == 1
    a = next(j for j in out["jobs"] if j["job_key"] == "a")
    assert a["change"] == "down" and (a["old_rank"], a["new_rank"]) == (1, 2)
    total = sum(r["score_delta"] for r in a["reasons"])
    assert total == pytest.approx(a["new_soft_score"] - a["old_soft_score"], abs=2e-3)
    assert any("weight 0.5 -> 0.2" in r["text"] for r in a["reasons"])
    assert {c["condition_id"] for c in out["condition_changes"]} == {"py", "rust"}


def test_unchanged_jobs_are_not_listed():
    env = {**conds(py=0.5), "kept": [job("a", 1, [row("py", 0.5, 1.0)])], "excluded": [], "unverified": []}
    assert explain_rank_changes(env, {**env, "condition_version": 2})["jobs"] == []


def build_api(snaps, cs):
    service, llm = make_service(snaps, cs)
    return service, TestClient(create_app(service)), llm


def test_relaxing_a_hard_condition_explains_who_came_back_and_why():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    _, client, _ = build_api([snap(1, location="London"), snap(2)], cs)
    tid = client.post("/search", json={"query": QUERY}).json()["task_id"]
    body = client.post(f"/tasks/{tid}/revise", json={"expected_version": 1, "strengths": {REGION.id: "soft"}}).json()
    entered = next(j for j in body["rank_changes"]["jobs"] if j["job_key"] == "greenhouse:1")
    assert entered["change"] == "entered" and entered["old_status"] == "excluded"
    assert '"Located in London."' in entered["reasons"][0]["text"] and "hard -> soft" in entered["reasons"][0]["text"]
    assert body["rank_changes"]["from_version"] == 1 and body["rank_changes"]["to_version"] == 2


def test_tightening_to_hard_explains_the_exclusion_with_its_quote():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION.model_copy(update={"strength": "soft"})])
    _, client, _ = build_api([snap(1, location="London"), snap(2)], cs)
    tid = client.post("/search", json={"query": QUERY}).json()["task_id"]
    body = client.post(f"/tasks/{tid}/revise", json={"expected_version": 1, "strengths": {REGION.id: "hard"}}).json()
    out = next(j for j in body["rank_changes"]["jobs"] if j["job_key"] == "greenhouse:1")
    assert out["change"] == "excluded" and "soft -> hard" in out["reasons"][0]["text"] and "London" in out["reasons"][0]["text"]


class SkillLLM:
    def __call__(self, system, user):
        text = re.search(r"<job>(.*)</job>", user, re.S).group(1)
        out = []
        for cid in re.findall(r'"condition_id": "([^"]+)"', user):
            hit = ("Python" if cid.startswith("skill") and "python" in cid.lower() else None)
            if cid.startswith("skill"):
                word = "Python" if cid == PY.id else "Rust"
                out.append({"condition_id": cid, "verdict": "support" if word in text else "unknown",
                            "quote": word if word in text else None, "reason": ""})
            else:
                out.append({"condition_id": cid, "verdict": "support", "quote": "LLM", "reason": ""})
        return json.dumps({"judgments": out})


PQ = "LLM 应用开发，最好会 Python，也希望有 Rust"
PY = Condition(field="skill", strength="soft", quote="Python", weight=0.5, value=TextValue(text="python"))
RUST = Condition(field="skill", strength="soft", quote="Rust", weight=0.5, value=TextValue(text="rust"))


def test_weight_revision_reorders_and_is_explained_through_the_api():
    cs = ConditionSet(raw_query=PQ, conditions=[FOCUS, PY, RUST])
    snaps = [snap(1, body="Build LLM applications with Python."), snap(2, body="Build LLM applications with Rust.")]
    service = SearchService(JobIndex(snaps + fillers()), None, Verifier(JudgmentCache(), complete=SkillLLM(), model="m"), TaskStore(),
                            parse=lambda q: cs, budget=Budget(target_kept=5))
    client = TestClient(create_app(service))
    first = client.post("/search", json={"query": PQ}).json()
    assert [j["title"] for j in first["kept"]] == ["Eng 1", "Eng 2"]           # equal scores: pipeline order
    r = client.post(f"/tasks/{first['task_id']}/revise",
                    json={"expected_version": 1, "weights": {RUST.id: 0.9, PY.id: 0.1}}).json()
    assert [j["title"] for j in r["kept"]] == ["Eng 2", "Eng 1"]
    moved = next(j for j in r["rank_changes"]["jobs"] if j["job_key"] == "greenhouse:2")
    assert moved["change"] == "up" and moved["reasons"][0]["score_delta"] > 0
    assert any("weight 0.5 -> 0.9" in x["text"] for x in moved["reasons"])


def test_weight_revision_is_validated():
    cs = ConditionSet(raw_query=PQ, conditions=[FOCUS, PY])
    service = SearchService(JobIndex([snap(1), *fillers()]), None, Verifier(JudgmentCache(), complete=SkillLLM(), model="m"), TaskStore(),
                            parse=lambda q: cs, budget=Budget(target_kept=5))
    tid = service.start(PQ)["task_id"]
    for kwargs in ({"weights": {PY.id: 3.0}}, {"weights": {FOCUS.id: 0.5}}, {"weights": {"skill:00000000": 0.5}}):
        with pytest.raises(InvalidRevision):
            service.revise(tid, 1, **kwargs)
