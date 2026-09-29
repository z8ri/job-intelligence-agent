"""LangGraph orchestration of one search run.

    retrieve -> rerank -> plan -> verify -> (retry_verify)* -> assemble

State is shared between nodes (conditions, candidates, verification result, retry count,
budget left). After `verify` the program, not the model, decides whether to go again:
it retries only when individual judgements failed for transient reasons (`judge failed`),
retries are left, and neither the LLM-call budget, the deadline nor the consecutive-failure
breaker has already stopped the run. Judgements that succeeded are cached, so a retry only
pays for the ones that failed. The loop is bounded by `max_retries`.
"""

from __future__ import annotations

import dataclasses
import time
from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.agent.models import ConditionSet
from src.agent.planning import DEFERRED_NOTE, plan_verification
from src.agent.rerank import Scorer, rerank
from src.agent.retrieval import JobIndex
from src.agent.verification import Budget, VerificationResult, Verifier

MEMO_LIMIT = 64
STOP_REASONS = ("llm call budget exhausted", "deadline reached", "too many consecutive failures")


class SearchState(TypedDict, total=False):
    conditions: ConditionSet
    budget: Budget
    query: str
    retrieval: object
    candidates: list
    rerank_trace: dict
    plan_trace: dict
    verification: VerificationResult
    retries: int
    max_retries: int
    llm_calls_used: int
    started: float
    timings: dict
    retry_log: list


def _should_retry(state: SearchState) -> bool:
    v = state["verification"]
    if state.get("retries", 0) >= state.get("max_retries", 0):
        return False
    if any(r in v.reasons for r in STOP_REASONS):
        return False
    return any(u.note.startswith("judge failed") for u in v.unverified)


def build_search_graph(index: JobIndex, scorer: Scorer | None, verifier: Verifier, *, retrieve_top_n: int, rerank_depth: int):
    # the index and scorer are fixed for the service's life, so a revision that leaves the retrieval
    # text unchanged (weights, strengths, dropping a non-role condition) reuses the earlier ranking
    retrieved: dict[str, object] = {}
    reranked: dict[str, object] = {}

    def retrieve(state: SearchState) -> dict:
        t = time.monotonic()
        res = retrieved.get(state["query"])
        if res is None:
            res = index.search(state["query"], top_n=retrieve_top_n)
            if len(retrieved) < MEMO_LIMIT and not any(str(i.get("status", "")).startswith("failed") for i in res.trace.get("channels", {}).values()):
                retrieved[state["query"]] = res
        return {"retrieval": res, "candidates": res.candidates, "rerank_trace": {"status": "skipped: no scorer"},
                "timings": {**state.get("timings", {}), "retrieval": time.monotonic() - t}}

    def do_rerank(state: SearchState) -> dict:
        t = time.monotonic()
        out: dict = {}
        if scorer is not None:
            rr = reranked.get(state["query"])
            if rr is None:
                rr = rerank(state["query"], index, state["candidates"], scorer, depth=rerank_depth)
                if len(reranked) < MEMO_LIMIT and not str(rr.trace.get("status", "")).startswith("failed"):
                    reranked[state["query"]] = rr
            out = {"candidates": rr.candidates, "rerank_trace": rr.trace}
        return {**out, "timings": {**state["timings"], "rerank": time.monotonic() - t}}

    def plan(state: SearchState) -> dict:
        ordered, trace = plan_verification(state["candidates"], index.snapshot, state["conditions"])
        return {"candidates": ordered, "plan_trace": trace}

    def verify(state: SearchState) -> dict:
        t = time.monotonic()
        budget: Budget = state["budget"]
        used = state.get("llm_calls_used", 0)
        remaining = dataclasses.replace(
            budget, max_llm_calls=max(0, budget.max_llm_calls - used),
            deadline_s=max(0.0, budget.deadline_s - (t - state["started"])),
        ) if state.get("retries", 0) else budget
        res = verifier.verify(state["candidates"], index.snapshot, state["conditions"], remaining)
        deferred = {d["job_key"] for d in state.get("plan_trace", {}).get("deferred", [])}
        for u in res.unverified:
            if u.note == "not checked" and u.candidate.job_key in deferred:
                u.note = DEFERRED_NOTE
        spent = res.stats.get("llm_calls", 0) + res.stats.get("failures", 0)
        timings = dict(state["timings"])
        timings["verification"] = timings.get("verification", 0.0) + (time.monotonic() - t)
        return {"verification": res, "llm_calls_used": used + spent, "timings": timings}

    def note_retry(state: SearchState) -> dict:
        failed = sum(1 for u in state["verification"].unverified if u.note.startswith("judge failed"))
        log = [*state.get("retry_log", []), {"attempt": state.get("retries", 0) + 1, "failed_judgements": failed}]
        return {"retries": state.get("retries", 0) + 1, "retry_log": log}

    def route(state: SearchState) -> str:
        return "retry" if _should_retry(state) else "done"

    g = StateGraph(SearchState)
    g.add_node("retrieve", retrieve)
    g.add_node("rerank", do_rerank)
    g.add_node("plan", plan)
    g.add_node("verify", verify)
    g.add_node("note_retry", note_retry)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "plan")
    g.add_edge("plan", "verify")
    g.add_conditional_edges("verify", route, {"retry": "note_retry", "done": END})
    g.add_edge("note_retry", "verify")
    return g.compile()
