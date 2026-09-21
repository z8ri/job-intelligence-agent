"""Unit tests for src/llm/answer_generation.py. OpenAI client is mocked — no
network calls, no API cost, deterministic. Focus: the grounding contract —
facts are rendered from the job record regardless of what the LLM says, and a
narrative with an inconsistent salary figure gets flagged.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.llm.answer_generation import (
    _extract_salary_mentions,
    _render_job_block,
    _salary_fact_check,
    format_fallback_answer,
    generate_answer,
)


def _job(**overrides):
    base = {
        "job_id": "j1",
        "company": "Acme",
        "title": "Backend Engineer",
        "location": "Remote",
        "remote": "remote",
        "salary_min": 140_000,
        "salary_max": 160_000,
        "tags": ["Python", "AWS"],
    }
    base.update(overrides)
    return base


def _fake_client(payload: dict):
    client = MagicMock()
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    resp.usage = MagicMock(prompt_tokens=200, completion_tokens=50)
    client.chat.completions.create.return_value = resp
    return client


class TestExtractSalaryMentions:
    def test_dollar_with_commas(self):
        assert _extract_salary_mentions("offers $150,000 base") == [150_000]

    def test_dollar_k_shorthand(self):
        assert _extract_salary_mentions("around $150k") == [150_000]

    def test_bare_k_shorthand(self):
        assert _extract_salary_mentions("roughly 150k a year") == [150_000]

    def test_ignores_implausible_numbers(self):
        # 5 years experience shouldn't be read as a salary
        assert _extract_salary_mentions("requires 5 years experience") == []


class TestSalaryFactCheck:
    def test_narrative_within_range_is_not_flagged(self):
        job = _job(salary_min=140_000, salary_max=160_000)
        assert _salary_fact_check("This pays around $150k", job) is None

    def test_narrative_outside_range_is_flagged(self):
        job = _job(salary_min=140_000, salary_max=160_000)
        warning = _salary_fact_check("This pays around $300k", job)
        assert warning is not None
        assert "300,000" in warning

    def test_no_salary_data_skips_check(self):
        job = _job(salary_min=None, salary_max=None)
        assert _salary_fact_check("This pays around $300k", job) is None

    def test_small_rounding_slack_is_tolerated(self):
        job = _job(salary_min=150_000, salary_max=150_000)
        # within the 5% tolerance band
        assert _salary_fact_check("about $155k", job) is None


class TestRenderJobBlock:
    def test_facts_come_from_job_record_not_narrative(self):
        job = _job(salary_min=140_000, salary_max=160_000, location="Austin, TX")
        block = _render_job_block(job, 1, "This is a narrative that never mentions numbers.")
        assert "$140,000-$160,000" in block
        assert "Austin, TX" in block

    def test_fact_check_warning_is_included_when_narrative_is_wrong(self):
        job = _job(salary_min=140_000, salary_max=160_000)
        block = _render_job_block(job, 1, "This role pays an incredible $500k")
        assert "Fact-check note" in block


class TestGenerateAnswer:
    def test_empty_jobs_returns_canned_message_without_calling_llm(self):
        with patch("src.llm.answer_generation.get_client") as mock_get_client:
            answer = generate_answer("some query", [])
        assert "No matching jobs found" in answer
        mock_get_client.assert_not_called()

    def test_renders_deterministic_facts_plus_llm_narrative(self):
        job = _job()
        payload = {"per_job": {"j1": "Great Python match."}, "summary": "Solid pick overall."}
        with patch("src.llm.answer_generation.get_client", return_value=_fake_client(payload)):
            answer = generate_answer("python jobs", [job])
        assert "Great Python match." in answer
        assert "$140,000-$160,000" in answer  # from the job record, not the LLM
        assert "Solid pick overall." in answer

    def test_missing_narrative_for_a_job_id_falls_back_gracefully(self):
        job = _job()
        payload = {"per_job": {}, "summary": ""}
        with patch("src.llm.answer_generation.get_client", return_value=_fake_client(payload)):
            answer = generate_answer("python jobs", [job])
        assert "no narrative returned" in answer

    def test_null_narrative_value_falls_back_instead_of_crashing(self):
        # Regression: a present-but-null per_job value used to reach the salary
        # regex as None and raise TypeError instead of falling back.
        job = _job()
        payload = {"per_job": {"j1": None}, "summary": ""}
        with patch("src.llm.answer_generation.get_client", return_value=_fake_client(payload)):
            answer = generate_answer("python jobs", [job])
        assert "no narrative returned" in answer

    def test_non_string_narrative_value_is_coerced_not_crashed(self):
        job = _job()
        payload = {"per_job": {"j1": {"unexpected": "shape"}}, "summary": ""}
        with patch("src.llm.answer_generation.get_client", return_value=_fake_client(payload)):
            answer = generate_answer("python jobs", [job])
        assert "unexpected" in answer

    def test_api_failure_raises_and_does_not_swallow_the_error(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("boom")
        with patch("src.llm.answer_generation.get_client", return_value=client):
            with pytest.raises(RuntimeError):
                generate_answer("python jobs", [_job()])


class TestFormatFallbackAnswer:
    def test_empty_jobs(self):
        assert "No matching jobs found" in format_fallback_answer([])

    def test_lists_jobs_without_any_llm_call(self):
        answer = format_fallback_answer([_job()])
        assert "Backend Engineer" in answer
        assert "Acme" in answer
