"""Lightweight LLM-call observability: latency, token usage, and estimated cost.

No external tracing service (Langfuse/LangSmith) — this project's call volume
doesn't justify the dependency. Each LLM call appends one JSON line to a trace
file; that's enough to answer "which node is slow" and "what did this session
cost" without needing a dashboard.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRACE_PATH = ROOT / "logs" / "pipeline_traces.jsonl"

# USD per token, input/output. Verify against https://openai.com/api/pricing/
# before treating these as authoritative — model pricing changes over time and
# this table is not kept in sync automatically.
_PRICING_PER_TOKEN = {
    "gpt-4o-mini": {"prompt": 0.15 / 1_000_000, "completion": 0.60 / 1_000_000},
    "text-embedding-3-small": {"prompt": 0.02 / 1_000_000, "completion": 0.0},
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """Returns None (rather than 0.0) for an unlisted model, so a missing price
    entry shows up as a gap in the trace instead of silently reading as free."""
    pricing = _PRICING_PER_TOKEN.get(model)
    if pricing is None:
        return None
    return prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]


def log_call(
    run_id: str | None,
    node: str,
    model: str,
    latency_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    success: bool = True,
    error: str | None = None,
    trace_path: Path | None = None,
) -> None:
    """Append one JSON line describing an LLM call. Never raises — a logging
    failure (e.g. read-only filesystem) must not take down the pipeline call
    it's trying to observe."""
    path = trace_path or DEFAULT_TRACE_PATH
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "run_id": run_id,
        "node": node,
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "estimated_cost_usd": estimate_cost_usd(model, prompt_tokens, completion_tokens),
        "success": success,
        "error": error,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


class timed_call:
    """Context manager measuring wall-clock latency in milliseconds.

    Usage:
        with timed_call() as t:
            response = client.chat.completions.create(...)
        log_call(..., latency_ms=t.elapsed_ms)
    """

    def __enter__(self):
        self._start = time.perf_counter()
        self.elapsed_ms = 0.0
        return self

    def __exit__(self, *exc_info):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
        return False
