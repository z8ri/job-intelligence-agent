import pytest
from pydantic import ValidationError

from src.agent.models import (
    Condition,
    ConditionSet,
    EmploymentValue,
    ExperienceValue,
    ModesValue,
    RegionsValue,
    SalaryValue,
    TextValue,
)

QUERY = "想找纽约可以工作的初级 LLM 应用开发全职岗位，可以混合办公，不希望主要做模型训练。"


def cond(field, value, quote, strength="hard"):
    return Condition(field=field, strength=strength, value=value, quote=quote)


def base_conditions():
    return [
        cond("role_focus", TextValue(text="LLM application development"), "LLM 应用开发"),
        cond("seniority", ExperienceValue(level="junior"), "初级"),
        cond("work_region", RegionsValue(regions=["New York"]), "纽约可以工作"),
        cond("remote_mode", ModesValue(modes=["hybrid"]), "可以混合办公", "soft"),
        cond("role_avoid", TextValue(text="primarily model training"), "不希望主要做模型训练", "soft"),
    ]


def test_field_must_match_value_kind():
    with pytest.raises(ValidationError):
        cond("salary", TextValue(text="150k"), "x")
    with pytest.raises(ValidationError):
        cond("work_region", ModesValue(modes=["remote"]), "x")


def test_id_is_stable_across_strength_and_quote():
    a = cond("role_focus", TextValue(text="LLM Application  Development"), "LLM 应用开发", "hard")
    b = cond("role_focus", TextValue(text="llm application development"), "应用开发", "soft")
    assert a.id == b.id
    assert a.signature() != b.signature()


def test_id_differs_for_different_values():
    a = cond("skill", TextValue(text="python"), "q")
    b = cond("skill", TextValue(text="rust"), "q")
    assert a.id != b.id


def test_region_order_and_case_do_not_change_id():
    a = cond("work_region", RegionsValue(regions=["New York", "Boston"]), "q")
    b = cond("work_region", RegionsValue(regions=["boston", "new york"]), "q")
    assert a.id == b.id


def test_salary_keeps_basis_currency_period_region():
    s = SalaryValue(currency="usd", period="year", basis="base", min_amount=150000, region="US")
    c = cond("salary", s, "150k")
    other = cond("salary", SalaryValue(currency="USD", period="year", basis="total", min_amount=150000, region="US"), "150k")
    assert c.id != other.id  # base vs total salary are different conditions


def test_condition_set_requires_verbatim_quote():
    bad = cond("role_focus", TextValue(text="x"), "这句话用户没说过")
    with pytest.raises(ValidationError):
        ConditionSet(raw_query=QUERY, conditions=[bad])


def test_condition_set_quote_check_ignores_whitespace_and_case():
    c = cond("skill", TextValue(text="llm"), "llm  应用开发")
    ConditionSet(raw_query=QUERY.replace("LLM", "LLM"), conditions=[c])  # no raise


def test_condition_set_rejects_duplicate_ids():
    a = cond("skill", TextValue(text="python"), "LLM")
    b = cond("skill", TextValue(text="Python"), "初级")
    with pytest.raises(ValidationError):
        ConditionSet(raw_query=QUERY, conditions=[a, b])


def test_retrieval_text_uses_only_work_content():
    cs = ConditionSet(raw_query=QUERY, conditions=base_conditions())
    text = cs.retrieval_text()
    assert "LLM application development" in text
    assert "model training" not in text  # role_avoid must not steer retrieval
    assert "New York" not in text


def test_retrieval_text_falls_back_to_raw_query():
    only_region = [cond("work_region", RegionsValue(regions=["New York"]), "纽约可以工作")]
    assert ConditionSet(raw_query=QUERY, conditions=only_region).retrieval_text() == QUERY


def test_hard_and_soft_split_and_get():
    cs = ConditionSet(raw_query=QUERY, conditions=base_conditions())
    assert {c.field for c in cs.hard()} == {"role_focus", "seniority", "work_region"}
    assert {c.field for c in cs.soft()} == {"remote_mode", "role_avoid"}
    first = cs.conditions[0]
    assert cs.get(first.id) == first
    assert cs.get("nope") is None


def test_revise_keeps_version_when_only_quote_changes():
    cs = ConditionSet(raw_query=QUERY, conditions=base_conditions())
    reworded_query = QUERY + " 谢谢"
    conds = list(cs.conditions)
    conds[0] = cond("role_focus", TextValue(text="LLM application development"), "应用开发")
    revised, changes = cs.revise(reworded_query, conds)
    assert changes.is_empty
    assert revised.version == cs.version
    assert revised.fingerprint() == cs.fingerprint()


def test_revise_bumps_version_on_strength_flip_and_reports_it():
    cs = ConditionSet(raw_query=QUERY, conditions=base_conditions())
    conds = list(cs.conditions)
    flipped = cond("remote_mode", ModesValue(modes=["hybrid"]), "可以混合办公", "hard")
    conds[3] = flipped
    revised, changes = cs.revise(QUERY, conds)
    assert revised.version == cs.version + 1
    assert changes.modified == [flipped.id]
    assert changes.changed_ids == {flipped.id}
    assert revised.fingerprint() != cs.fingerprint()


def test_revise_reports_added_and_removed():
    cs = ConditionSet(raw_query=QUERY, conditions=base_conditions())
    added = cond("employment_type", EmploymentValue(types=["full_time"]), "全职")
    conds = [c for c in cs.conditions if c.field != "seniority"] + [added]
    revised, changes = cs.revise(QUERY, conds)
    assert changes.added == [added.id]
    assert len(changes.removed) == 1 and changes.removed[0].startswith("seniority:")
    assert revised.version == 2


def test_condition_serialization_roundtrip_keeps_id():
    cs = ConditionSet(raw_query=QUERY, conditions=base_conditions())
    again = ConditionSet.model_validate_json(cs.model_dump_json())
    assert [c.id for c in again.conditions] == [c.id for c in cs.conditions]
    assert '"id"' in cs.model_dump_json()
