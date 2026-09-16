"""
LangGraph pipeline: 8 main nodes + 1 reject branch + 1 bounded retry loop.

Flow:
  query_understanding ──[is_job_query=True]──> query_expansion → candidate_loading
                                              → unified_scoring → collection_fusion
                                              → verification ──[valid_count>0 or retried]──> classification → answer_generation → END
                                                             ──[valid_count==0 and retry_count<1]──> unified_scoring (retry, at most once)
                       ──[is_job_query=False]─> reject → END

Nodes:
  1. query_understanding  — LLM extracts structured preferences AND classifies intent
  2. query_expansion      — expand keywords/tags via QueryExpander
  3. candidate_loading    — load jobs from MySQL with hard filters
  4. unified_scoring      — TF-IDF/BM25/Dense/RRF retrieval + optional LLM reranking + multi-field ScoringEngine
  5. collection_fusion    — normalize scores across sources, top-K
  6. verification         — mark valid/rejected/unknown; if 0 valid, retry once (switch retrieval strategy, never relax hard filters)
  7. classification       — predict job category (fallback if model absent)
  8. answer_generation    — LLM generates natural language answer
  R. reject               — produce a polite refusal for non-job queries
"""

import sys

from langgraph.graph import StateGraph, END

from src.pipeline.state import PipelineState

# LLM preprocessing/postprocessing + scoring + persistence
from src.llm.query_understanding import parse_preferences
from src.db.database import load_candidates
from src.db.memory import load_memory, save_memory, merge_preferences
from src.scoring.fusion import fuse_and_rank
from src.scoring.reranker import rerank
from src.scoring.verifier import verify_jobs
from src.llm.answer_generation import generate_answer
from src.classification.classifier import JobClassifier

# Retrieval + query expansion
from src.ir.query_expansion import QueryExpander
from src.ir.tfidf import JobIRSystem
from src.ir.bm25 import JobBM25System
from src.ir.dense import JobDenseSystem
from src.ir.rrf import reciprocal_rank_fusion
from src.scoring.engine import ScoringEngine


# ---------------------------------------------------------------------------
# Constrained planner: retrieval_mode from query_understanding -> concrete retrieval config
# ---------------------------------------------------------------------------

_PLANNER_MODE_MAP = {
    # Precise tech terms / explicit skills -> pure BM25 lexical matching. No need for
    # dense fuzzy semantics or reranking (avoids dense pulling in jobs that are
    # conceptually similar but have different actual responsibilities).
    "exact": {"ir_mode": "bm25", "use_reranker": False},
    # Responsibility-style descriptions whose keywords may not literally appear in
    # the job text -> BM25 + Dense fused via RRF.
    "semantic": {"ir_mode": "hybrid_rrf", "use_reranker": False},
    # Query carries very little information -> semantic plus reranking, adding one
    # more layer of judgment to compensate for the weak retrieval signal.
    "exploratory": {"ir_mode": "hybrid_rrf", "use_reranker": True},
}


# ---------------------------------------------------------------------------
# Module singletons
# ---------------------------------------------------------------------------

_query_expander: QueryExpander | None = None
_scoring_engine: ScoringEngine | None = None
_ir_system: JobIRSystem | None = None
_bm25_system: JobBM25System | None = None
_dense_system: JobDenseSystem | None = None


def _get_query_expander() -> QueryExpander:
    global _query_expander
    if _query_expander is None:
        _query_expander = QueryExpander()
    return _query_expander


def _get_scoring_engine() -> ScoringEngine:
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = ScoringEngine()
    return _scoring_engine


def _get_ir_system() -> JobIRSystem:
    """tfidf_model.pkl was trained via `python -m src.ir.tfidf`, so the pickled
    tokenizer references __main__.JobIRSystem. Loading it from any entry point
    other than src.ir.tfidf raises AttributeError; inject the class into the
    current __main__ as a workaround.
    """
    global _ir_system
    if _ir_system is None:
        import __main__
        if not hasattr(__main__, "JobIRSystem"):
            __main__.JobIRSystem = JobIRSystem
        ir = JobIRSystem()
        ir.load_model()
        _ir_system = ir
    return _ir_system


def _get_bm25_system() -> JobBM25System:
    global _bm25_system
    if _bm25_system is None:
        bm25 = JobBM25System()
        bm25.load_model()
        _bm25_system = bm25
    return _bm25_system


def _get_dense_system() -> JobDenseSystem:
    global _dense_system
    if _dense_system is None:
        dense = JobDenseSystem()
        dense.load_model()
        _dense_system = dense
    return _dense_system


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

_EMPTY_SIGNAL_FIELDS = [
    "description_keywords", "target_salary", "preferred_location",
    "remote_preference", "desired_tags", "preferred_category",
]


def node_query_understanding(state: PipelineState) -> dict:
    """Extract structured preferences AND classify intent (is_job_query) via LLM.

    When a session_id is given, merge with stored memory (fields explicitly
    mentioned this turn override memory; unmentioned fields fall back to it).
    Only ask a clarifying question on a true cold start where the merged
    preferences still carry no usable signal at all. The exploratory mode is
    designed to handle vague queries, so vagueness alone must not trigger
    clarification, or the upstream work is wasted.
    """
    result = parse_preferences(state["user_query"], state.get("api_key"))
    prefs = result["preferences"]
    is_job_query = bool(prefs.get("is_job_query", True))

    session_id = state.get("session_id")
    had_memory = False
    if session_id and is_job_query:
        memory = load_memory(session_id)
        had_memory = bool(memory)
        prefs = merge_preferences(prefs, memory)
        save_memory(session_id, prefs)  # persist the merged, up-to-date full profile

    needs_clarification = (
        is_job_query
        and not had_memory
        and prefs.get("retrieval_mode") == "exploratory"
        and all(not prefs.get(f) for f in _EMPTY_SIGNAL_FIELDS)
    )

    return {
        "is_job_query": is_job_query,
        "needs_clarification": needs_clarification,
        "preferences": prefs,
        "weights": result["weights"],
    }


def node_reject(state: PipelineState) -> dict:
    """Polite refusal when the query is not job-related."""
    msg = (
        "I'm a job search assistant — I can only help with tech job recommendations.\n\n"
        "Try asking something like:\n"
        "- *senior python engineer remote $150k+*\n"
        "- *frontend job in NYC, hybrid welcomed*\n"
        "- *ML internship for non-CS major*"
    )
    return {"answer": msg, "classified_jobs": []}


def node_clarify(state: PipelineState) -> dict:
    """Ask a clarifying question instead of guessing when there is no usable
    signal; only triggered on a true cold start with all fields empty."""
    msg = (
        "I'd like to help, but I need a bit more to go on — "
        "what kind of role, tech stack, location, or salary range are you looking for?\n\n"
        "For example: *remote backend engineer, Python, around $150k*"
    )
    return {"answer": msg, "classified_jobs": []}


def node_query_expansion(state: PipelineState) -> dict:
    """Expand keywords and tags using synonym/hierarchy tables."""
    config = state.get("config") or {}
    prefs = state["preferences"]

    if config.get("skip_expansion"):
        return {
            "expanded_keywords": prefs.get("description_keywords") or [],
            "expanded_tags": prefs.get("desired_tags") or [],
        }

    qe = _get_query_expander()
    kw, tags = qe.expand_query(
        prefs.get("description_keywords"),
        prefs.get("desired_tags"),
    )
    return {"expanded_keywords": kw, "expanded_tags": tags}


def node_candidate_loading(state: PipelineState) -> dict:
    """Load candidate jobs from MySQL, applying hard filters."""
    candidates = load_candidates(state["preferences"].get("hard_filters") or None)
    return {"candidates": candidates}


def node_unified_scoring(state: PipelineState) -> dict:
    """Score each candidate: TF-IDF / BM25 / hybrid + multi-field via ScoringEngine."""
    prefs = state["preferences"]
    config = state.get("config") or {}

    expanded_kw = state.get("expanded_keywords") or []
    text_query = " ".join(expanded_kw) if expanded_kw else state["user_query"]

    # Constrained planner: query_understanding has already decided which retrieval
    # strategy this query needs (exact/semantic/exploratory); map it to a concrete
    # ir_mode/reranker combination here. An explicitly passed config takes
    # precedence over the planner's choice, so CLI debugging and the ablation
    # configs in src/eval/* keep behaving exactly as before.
    plan = _PLANNER_MODE_MAP.get(prefs.get("retrieval_mode"), {})
    ir_mode = (config.get("ir_mode") or plan.get("ir_mode") or "tfidf").lower()
    use_reranker = config["use_reranker"] if "use_reranker" in config else plan.get("use_reranker", False)
    if ir_mode == "bm25":
        text_scores = _get_bm25_system().get_similarities(text_query)
    elif ir_mode == "dense":
        text_scores = _get_dense_system().get_similarities(text_query)
    elif ir_mode == "hybrid":
        tfidf_s = _get_ir_system().get_similarities(text_query)
        bm25_s = _get_bm25_system().get_similarities(text_query)
        all_ids = set(tfidf_s) | set(bm25_s)
        text_scores = {
            jid: 0.5 * tfidf_s.get(jid, 0.0) + 0.5 * bm25_s.get(jid, 0.0)
            for jid in all_ids
        }
    elif ir_mode == "hybrid_rrf":
        # BM25 (lexical) + Dense (semantic) fused by rank via RRF rather than a
        # weighted average of raw scores: the two score scales differ, and a
        # direct average would be dominated by the larger-scale source.
        bm25_s = _get_bm25_system().get_similarities(text_query)
        dense_s = _get_dense_system().get_similarities(text_query)
        fused = reciprocal_rank_fusion([bm25_s, dense_s])
        # Raw RRF values are tiny (max about 2/(k+1) with two sources), so they must
        # be min-max rescaled to [0,1] to match the magnitude of the other
        # ScoringEngine fields (salary/location/tags/...). Otherwise the description
        # weight (largest by default, 0.35) is completely drowned out and hybrid_rrf
        # effectively stops ranking by text relevance.
        if fused:
            f_min, f_max = min(fused.values()), max(fused.values())
            if f_max > f_min:
                text_scores = {jid: (s - f_min) / (f_max - f_min) for jid, s in fused.items()}
            else:
                text_scores = {jid: 0.0 for jid in fused}
        else:
            text_scores = {}
    else:
        text_scores = _get_ir_system().get_similarities(text_query)

    if use_reranker:
        # Make a finer-grained query-job relevance judgment on the first-stage
        # Top-N and overwrite their coarse scores. Use the original user_query,
        # not text_query (which query_expansion may have expanded), because the
        # question is "does this satisfy the user's stated intent", not keyword overlap.
        ranked_candidates = sorted(
            state["candidates"], key=lambda j: text_scores.get(j["job_id"], 0.0), reverse=True
        )
        reranked = rerank(state["user_query"], ranked_candidates, api_key=state.get("api_key"))
        text_scores.update(reranked)  # only the reranked Top-N are overwritten; the rest keep their coarse scores

    weight_adjustments = prefs.get("weight_adjustments") or {}
    engine = _get_scoring_engine()
    equal_weights = bool(config.get("equal_weights"))

    scored = []
    for job in state["candidates"]:
        tfidf = text_scores.get(job["job_id"], 0.0)
        final_score, breakdown = engine.compute_final_score(
            job, prefs, tfidf, weight_adjustments=weight_adjustments
        )
        if equal_weights and breakdown:
            final_score = round(sum(breakdown.values()) / len(breakdown), 4)

        job["final_score"] = final_score
        job["score_breakdown"] = breakdown
        scored.append(job)
    return {"scored_jobs": scored}


def node_collection_fusion(state: PipelineState) -> dict:
    """Normalize scores across data sources and select top-K.

    dedupe=True: the monthly HN threads cause the same posting to be stored under
    multiple job_ids, so dedupe by (company, title). pool_eval does not call this
    node (it evaluates its 12 configs flat on its own), so eval numbers are unaffected.
    """
    top_k = state.get("top_k") or 10
    ranked = fuse_and_rank(state["scored_jobs"], top_k=top_k, dedupe=True)
    return {"ranked_jobs": ranked}


def node_verification(state: PipelineState) -> dict:
    """Verify ranked_jobs and mark each valid/rejected/unknown. If there are zero
    valid results and no retry has happened yet, trigger a single retry with a
    stronger retrieval strategy (hard_filters are left untouched; hard
    constraints are never relaxed).
    """
    jobs = verify_jobs(state["ranked_jobs"], state["preferences"], state["user_query"])
    valid_count = sum(1 for j in jobs if j["verification_status"] == "valid")
    retry_count = state.get("retry_count", 0)
    verified = [j for j in jobs if j["verification_status"] != "rejected"]

    if valid_count == 0 and retry_count < 1:
        # Escalate to the strongest retrieval combination currently available. If
        # this round was already hybrid_rrf + rerank, the retry changes nothing in
        # practice; this is a known limitation. The spec only requires "retry at
        # most once", not that the retry is guaranteed to help.
        config = dict(state.get("config") or {})
        config["ir_mode"] = "hybrid_rrf"
        config["use_reranker"] = True
        return {
            "verified_jobs": verified,
            "retry_count": retry_count + 1,
            "should_retry": True,
            "config": config,
        }

    return {
        "verified_jobs": verified,
        "retry_count": retry_count,
        "should_retry": False,
    }


def _route_after_verification(state: PipelineState) -> str:
    return "retry" if state.get("should_retry") else "continue"


def node_classification(state: PipelineState) -> dict:
    """Predict job category for each ranked result."""
    import src.classification.classifier as clf_mod

    jobs = state["verified_jobs"]
    try:
        if clf_mod._classifier_instance is None:
            clf_mod.load_classifier()
        texts = [JobClassifier.prepare_text(job) for job in jobs]
        results = clf_mod._classifier_instance.predict_batch(texts)
        for job, (predicted, scores) in zip(jobs, results):
            job["predicted_category"] = predicted
            job["category_scores"] = scores
    except Exception:
        # Fallback: use existing category from database
        for job in jobs:
            job["predicted_category"] = job.get("category", "other")
            job["category_scores"] = {}

    return {"classified_jobs": list(jobs)}


def node_answer_generation(state: PipelineState) -> dict:
    """Generate natural language answer via LLM."""
    answer = generate_answer(
        user_query=state["user_query"],
        ranked_jobs=state["classified_jobs"],
        preferences=state.get("preferences"),
        api_key=state.get("api_key"),
    )
    return {"answer": answer}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _route_after_understanding(state: PipelineState) -> str:
    """Route to retrieval / reject / clarify based on is_job_query + needs_clarification."""
    if not state.get("is_job_query", True):
        return "reject"
    if state.get("needs_clarification"):
        return "clarify"
    return "query_expansion"


def build_graph():
    """Build and compile the LangGraph pipeline (8 main nodes + reject/clarify branches)."""
    graph = StateGraph(PipelineState)

    graph.add_node("query_understanding", node_query_understanding)
    graph.add_node("query_expansion", node_query_expansion)
    graph.add_node("candidate_loading", node_candidate_loading)
    graph.add_node("unified_scoring", node_unified_scoring)
    graph.add_node("collection_fusion", node_collection_fusion)
    graph.add_node("verification", node_verification)
    graph.add_node("classification", node_classification)
    graph.add_node("answer_generation", node_answer_generation)
    graph.add_node("reject", node_reject)
    graph.add_node("clarify", node_clarify)

    graph.set_entry_point("query_understanding")
    graph.add_conditional_edges(
        "query_understanding",
        _route_after_understanding,
        {"query_expansion": "query_expansion", "reject": "reject", "clarify": "clarify"},
    )
    graph.add_edge("query_expansion", "candidate_loading")
    graph.add_edge("candidate_loading", "unified_scoring")
    graph.add_edge("unified_scoring", "collection_fusion")
    graph.add_edge("collection_fusion", "verification")
    graph.add_conditional_edges(
        "verification",
        _route_after_verification,
        {"retry": "unified_scoring", "continue": "classification"},
    )
    graph.add_edge("classification", "answer_generation")
    graph.add_edge("answer_generation", END)
    graph.add_edge("reject", END)
    graph.add_edge("clarify", END)

    return graph.compile()


_compiled_app = None


def run_pipeline(
    user_query: str,
    api_key: str | None = None,
    top_k: int = 10,
    config: dict | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Run the full pipeline end-to-end.

    Args:
        user_query: natural language job search query
        api_key: OpenAI API key (default: from env)
        top_k: number of results to return
        config: ablation experiment flags (e.g., {"skip_expansion": True})
        session_id: session identifier for cross-turn preference memory; None means single-turn, stateless

    Returns:
        Final PipelineState dict with all intermediate + final results
    """
    global _compiled_app
    if _compiled_app is None:
        _compiled_app = build_graph()
    app = _compiled_app
    initial_state = {
        "user_query": user_query,
        "api_key": api_key,
        "top_k": top_k,
        "config": config or {},
        "session_id": session_id,
    }
    return app.invoke(initial_state)


if __name__ == "__main__":
    import argparse

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Run the full pipeline once (smoke test)"
    )
    parser.add_argument("query", nargs="+", help="natural language query")
    parser.add_argument(
        "--ir-mode",
        choices=["tfidf", "bm25", "dense", "hybrid", "hybrid_rrf"],
        default=None,
        help="retrieval mode; defaults to tfidf if omitted",
    )
    parser.add_argument(
        "--rerank", action="store_true",
        help="LLM-rerank the Top-N first-stage candidates",
    )
    parser.add_argument(
        "--session", default=None,
        help="session ID for sharing preference memory across calls (reuse the same id to simulate a multi-turn conversation)",
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    config = {}
    if args.ir_mode:
        config["ir_mode"] = args.ir_mode
    if args.rerank:
        config["use_reranker"] = True

    print(f"Query: {query}\n")
    result = run_pipeline(query, config=config, session_id=args.session)
    print(f"Answer:\n{result.get('answer', 'No answer')}")
