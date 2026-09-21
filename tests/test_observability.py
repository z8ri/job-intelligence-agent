"""Unit tests for src/observability.py. No network calls; log_call writes to a
temp path so tests never touch the real logs/pipeline_traces.jsonl.
"""

import json

from src.observability import estimate_cost_usd, log_call


class TestEstimateCost:
    def test_known_model_computes_expected_cost(self):
        cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
        assert cost == 0.15 + 0.60

    def test_zero_tokens_costs_zero(self):
        assert estimate_cost_usd("gpt-4o-mini", 0, 0) == 0.0

    def test_unknown_model_returns_none_not_zero(self):
        # None (not 0.0) so a missing price entry is visible as a gap, not
        # silently misread as "this call was free".
        assert estimate_cost_usd("some-future-model", 100, 100) is None


class TestLogCall:
    def test_writes_one_json_line_with_expected_fields(self, tmp_path):
        trace_path = tmp_path / "trace.jsonl"
        log_call(
            run_id="run-1", node="query_understanding", model="gpt-4o-mini",
            latency_ms=123.456, prompt_tokens=10, completion_tokens=5,
            trace_path=trace_path,
        )
        lines = trace_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["run_id"] == "run-1"
        assert record["node"] == "query_understanding"
        assert record["latency_ms"] == 123.5  # rounded to 1 decimal
        assert record["success"] is True
        assert record["error"] is None
        assert record["estimated_cost_usd"] == estimate_cost_usd("gpt-4o-mini", 10, 5)

    def test_failure_call_is_recorded_with_error_message(self, tmp_path):
        trace_path = tmp_path / "trace.jsonl"
        log_call(
            run_id="run-2", node="answer_generation", model="gpt-4o-mini",
            latency_ms=10.0, success=False, error="boom", trace_path=trace_path,
        )
        record = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
        assert record["success"] is False
        assert record["error"] == "boom"

    def test_appends_across_multiple_calls(self, tmp_path):
        trace_path = tmp_path / "trace.jsonl"
        log_call(run_id="a", node="n", model="gpt-4o-mini", latency_ms=1.0, trace_path=trace_path)
        log_call(run_id="b", node="n", model="gpt-4o-mini", latency_ms=2.0, trace_path=trace_path)
        assert len(trace_path.read_text(encoding="utf-8").splitlines()) == 2

    def test_creates_parent_directory_if_missing(self, tmp_path):
        trace_path = tmp_path / "nested" / "dir" / "trace.jsonl"
        log_call(run_id="a", node="n", model="gpt-4o-mini", latency_ms=1.0, trace_path=trace_path)
        assert trace_path.exists()
