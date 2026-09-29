import json
import re
import threading

import pytest
from pydantic import ValidationError

from src.agent.models import Condition, ConditionSet, RegionsValue, TextValue
from src.agent.retrieval import JobIndex
from src.agent.scoring import soft_breakdown, soft_score
from src.agent.evidence import JobJudgment, Judgment
from src.agent.service import SearchService
from src.agent.snapshots import Snapshot
from src.agent.tasks import TaskStore
from src.agent.verification import Budget, JudgmentCache, Verifier
from tests.test_agent_verification import FakeLLM

QUERY = "想找纽约的 LLM 应用开发岗位，最好会 Python，也希望有 Rust"
REGION = Condition(field="work_region", strength="hard", quote="纽约", value=RegionsValue(regions=["New York"]))
FOCUS = Condition(field="role_focus", strength="hard", quote="LLM 应用开发", value=TextValue(text="LLM applications"))


def skill(text, quote, weight=None):
    return Condition(field="skill", strength="soft", quote=quote, value=TextValue(text=text), weight=weight)


PY, RUST = skill("python", "Python"), skill("rust", "Rust")


def test_weight_defaults_and_bounds():
    assert REGION.effective_weight == 1.0 and PY.effective_weight == 0.5
    assert skill("python", "Python", 0.9).effective_weight == 0.9
    with pytest.raises(ValidationError):
        skill("python", "Python", 1.5)


def test_weight_change_bumps_version_but_keeps_condition_id_and_cache_key():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, PY])
    heavier = PY.model_copy(update={"weight": 0.9})
    revised, changes = cs.revise(QUERY, [FOCUS, heavier])
    assert PY.id == heavier.id  # judgements stay valid: same id, no new LLM calls needed
    assert revised.version == 2 and changes.modified == [PY.id]
    assert revised.fingerprint() != cs.fingerprint()
    assert cs.revise(QUERY, [FOCUS, PY])[0].version == 1


def test_soft_score_is_weighted_mean_with_neutral_unknown():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, skill("python", "Python", 0.8), skill("rust", "Rust", 0.2)])
    py, rust = cs.soft()
    jj = JobJudgment(job_key="k", content_hash="h", condition_version=1, judgments={
        py.id: Judgment(condition_id=py.id, verdict="support"), rust.id: Judgment(condition_id=rust.id, verdict="conflict"),
    })
    bd = soft_breakdown(cs, jj)
    assert [b["score"] for b in bd] == [1.0, 0.0]
    assert soft_score(bd) == 0.8
    assert soft_score([]) is None
    unknown = JobJudgment(job_key="k", content_hash="h", condition_version=1, judgments={})
    assert soft_score(soft_breakdown(cs, unknown)) == 0.5


class TextLLM:
    """Supports python/rust by keyword, role_focus/region always; can fail transiently per title."""

    def __init__(self, flaky=None, fail_always=()):
        self.flaky = dict(flaky or {})  # title -> number of initial failures
        self.fail_always = set(fail_always)
        self.calls = []
        self._lock = threading.Lock()

    def __call__(self, system, user):
        title = re.search(r"Title: (.*)", user).group(1)
        text = re.search(r"<job>(.*)</job>", user, re.S).group(1)
        with self._lock:
            self.calls.append(title)
            if title in self.fail_always:
                raise RuntimeError("upstream 500")
            if self.flaky.get(title, 0) > 0:
                self.flaky[title] -= 1
                raise RuntimeError("timeout")
        out = []
        for cid in re.findall(r'"condition_id": "([^"]+)"', user):
            if cid.startswith("skill"):
                word = "Python" if PY.id == cid else "Rust"
                out.append({"condition_id": cid, "verdict": "support" if word in text else "unknown",
                            "quote": word if word in text else None, "reason": ""})
            elif cid.startswith("work_region"):
                out.append({"condition_id": cid, "verdict": "support", "quote": "New York", "reason": ""})
            else:
                out.append({"condition_id": cid, "verdict": "support", "quote": "LLM", "reason": ""})
        return json.dumps({"judgments": out})


def snaps():
    bodies = ["New York LLM applications team.", "New York LLM applications with Python.",
              "New York LLM applications with Python and Rust.", "New York LLM applications team."]
    return [Snapshot.create(source="greenhouse", source_job_id=str(i), title=f"Eng {i}", raw_content=b,
                            fetched_at="2026-03-01T00:00:00+00:00") for i, b in enumerate(bodies)] + [
        Snapshot.create(source="greenhouse", source_job_id="x1", title="Cook", raw_content="Cook meals.", fetched_at="2026-03-01T00:00:00+00:00"),
        Snapshot.create(source="greenhouse", source_job_id="x2", title="Driver", raw_content="Drive trucks.", fetched_at="2026-03-01T00:00:00+00:00"),
    ]


def build(cs, llm, *, max_retries=1, budget=None):
    return SearchService(JobIndex(snaps()), None, Verifier(JudgmentCache(), complete=llm, model="m"), TaskStore(),
                         parse=lambda q: cs, budget=budget or Budget(target_kept=5), max_retries=max_retries)


def test_soft_preferences_order_the_kept_jobs():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION, skill("python", "Python", 0.9), skill("rust", "Rust", 0.2)])
    body = build(cs, TextLLM()).start(QUERY)
    order = [j["title"] for j in body["kept"]]
    assert order[0] == "Eng 2" and order[1] == "Eng 1"  # both skills > python only > neither
    assert [j["rank"] for j in body["kept"]] == list(range(1, len(order) + 1))
    top = body["kept"][0]
    assert top["soft_score"] == 1.0 and {b["field"] for b in top["soft_breakdown"]} == {"skill"}
    assert body["kept"][-1]["soft_score"] == 0.5  # unknown is neutral, not a penalty


def test_weights_change_the_order():
    def order(w_py, w_rust):
        cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION, skill("python", "Python", w_py), skill("rust", "Rust", w_rust)])
        return [j["title"] for j in build(cs, TextLLM()).start(QUERY)["kept"][:3]]

    assert order(0.9, 0.1)[:2] == ["Eng 2", "Eng 1"]
    hard_only = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    assert all(j["soft_score"] is None for j in build(hard_only, TextLLM()).start(QUERY)["kept"])


def test_transient_failure_is_retried_once_and_only_failed_calls_are_repaid():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    llm = TextLLM(flaky={"Eng 1": 1})
    body = build(cs, llm, max_retries=1).start(QUERY)
    assert body["status"] == "complete" and "Eng 1" in [j["title"] for j in body["kept"]]
    assert body["trace"]["retries"] == [{"attempt": 1, "failed_judgements": 1}]
    assert llm.calls.count("Eng 1") == 2 and llm.calls.count("Eng 0") == 1  # successes were cached


def test_retries_are_bounded_and_failure_is_reported():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    llm = TextLLM(fail_always={"Eng 1"})
    body = build(cs, llm, max_retries=2).start(QUERY)
    assert llm.calls.count("Eng 1") == 3  # first try + two retries, then stop
    assert body["status"] == "partial" and "1 judgement(s) failed after retries" in body["reasons"]
    assert "Eng 1" not in [j["title"] for j in body["kept"]]
    assert len(body["trace"]["retries"]) == 2


def test_no_retry_when_the_breaker_or_budget_already_stopped_the_run():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    llm = FakeLLM(fail_all=True)
    body = build(cs, llm, max_retries=3, budget=Budget(target_kept=5, max_consecutive_failures=2)).start(QUERY)
    assert "too many consecutive failures" in body["reasons"]
    assert body["trace"]["retries"] == [] and len(llm.calls) <= 4  # not multiplied by retries
    capped = build(cs, TextLLM(), max_retries=3, budget=Budget(target_kept=5, max_llm_calls=1)).start(QUERY)
    assert "llm call budget exhausted" in capped["reasons"] and capped["trace"]["retries"] == []


def test_retry_respects_remaining_call_budget():
    cs = ConditionSet(raw_query=QUERY, conditions=[FOCUS, REGION])
    llm = TextLLM(fail_always={"Eng 0"})
    build(cs, llm, max_retries=5, budget=Budget(target_kept=5, max_llm_calls=6)).start(QUERY)
    assert len(llm.calls) <= 6


def test_parser_accepts_weight_on_soft_conditions_and_rejects_out_of_range():
    from src.agent.conditions import parse_conditions

    payload = {"conditions": [
        {"field": "role_focus", "strength": "hard", "quote": "LLM 应用开发", "value": {"kind": "text", "text": "LLM applications"}},
        {"field": "skill", "strength": "soft", "quote": "Python", "weight": 0.9, "value": {"kind": "text", "text": "python"}},
        {"field": "skill", "strength": "soft", "quote": "Rust", "weight": 7, "value": {"kind": "text", "text": "rust"}},
    ]}
    cs = parse_conditions(QUERY, complete=lambda s, u: json.dumps(payload), max_attempts=1)
    assert [c.effective_weight for c in cs.conditions] == [1.0, 0.9]  # the invalid one is dropped, not fatal
