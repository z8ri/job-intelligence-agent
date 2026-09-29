import json

import pytest

from src.agent.conditions import ConditionParseError, parse_conditions

QUERY = "想找纽约可以工作的初级 LLM 应用开发全职岗位，可以混合办公，不希望主要做模型训练。"


def good_payload():
    return {
        "conditions": [
            {"field": "role_focus", "strength": "hard", "quote": "LLM 应用开发",
             "value": {"kind": "text", "text": "LLM application development"}},
            {"field": "work_region", "strength": "hard", "quote": "纽约可以工作",
             "value": {"kind": "regions", "regions": ["New York"]}},
            {"field": "role_avoid", "strength": "soft", "quote": "不希望主要做模型训练",
             "value": {"kind": "text", "text": "primarily model training"}},
        ],
        "clarifications": [],
    }


class Scripted:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, system, user):
        self.calls.append((system, user))
        out = self.outputs.pop(0)
        return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)


def test_parses_valid_output_in_one_call():
    fake = Scripted(good_payload())
    cs = parse_conditions(QUERY, complete=fake)
    assert len(fake.calls) == 1
    assert {c.field for c in cs.conditions} == {"role_focus", "work_region", "role_avoid"}
    assert cs.version == 1
    assert cs.raw_query == QUERY


def test_empty_query_rejected_without_calling_llm():
    fake = Scripted()
    with pytest.raises(ConditionParseError):
        parse_conditions("   ", complete=fake)
    assert fake.calls == []


def test_non_verbatim_quote_triggers_retry_with_feedback():
    bad = good_payload()
    bad["conditions"][0]["quote"] = "LLM application development"  # translated, not in the query
    fake = Scripted(bad, good_payload())
    cs = parse_conditions(QUERY, complete=fake)
    assert len(fake.calls) == 2
    assert "not verbatim" in fake.calls[1][1]
    assert len(cs.conditions) == 3


def test_last_attempt_keeps_valid_and_drops_invalid():
    bad = good_payload()
    bad["conditions"][0]["quote"] = "made up words"
    fake = Scripted(bad, bad)
    cs = parse_conditions(QUERY, complete=fake)
    assert {c.field for c in cs.conditions} == {"work_region", "role_avoid"}


def test_wrong_value_kind_is_dropped_not_fatal():
    bad = good_payload()
    bad["conditions"][1]["value"] = {"kind": "text", "text": "New York"}  # region needs regions kind
    fake = Scripted(bad, bad)
    cs = parse_conditions(QUERY, complete=fake)
    assert "work_region" not in {c.field for c in cs.conditions}


def test_invalid_json_then_recovery():
    fake = Scripted("not json at all", good_payload())
    cs = parse_conditions(QUERY, complete=fake)
    assert len(fake.calls) == 2
    assert "not valid JSON" in fake.calls[1][1]
    assert len(cs.conditions) == 3


def test_raises_when_nothing_valid():
    fake = Scripted("nope", "still nope")
    with pytest.raises(ConditionParseError):
        parse_conditions(QUERY, complete=fake)


def test_raises_when_all_conditions_invalid():
    bad = {"conditions": [{"field": "skill", "strength": "hard", "quote": "nope",
                           "value": {"kind": "text", "text": "x"}}]}
    with pytest.raises(ConditionParseError):
        parse_conditions(QUERY, complete=Scripted(bad, bad))


def test_duplicate_conditions_are_collapsed():
    payload = good_payload()
    payload["conditions"].append(dict(payload["conditions"][0]))
    cs = parse_conditions(QUERY, complete=Scripted(payload))
    assert len(cs.conditions) == 3


def test_clarifications_are_kept_and_bad_ones_skipped():
    payload = good_payload()
    payload["clarifications"] = [
        {"question": "Fully remote only?", "reason": "changes qualification", "options": ["yes", "no"],
         "affects": ["remote_mode"]},
        {"reason": "missing question"},
    ]
    cs = parse_conditions(QUERY, complete=Scripted(payload))
    assert len(cs.clarifications) == 1
    assert cs.clarifications[0].affects == ["remote_mode"]
