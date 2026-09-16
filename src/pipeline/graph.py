"""
LangGraph pipeline: 8 main nodes + 1 reject branch + 1 bounded retry loop.

Flow:
  query_understanding ──[is_job_query=True]──> query_expansion → candidate_loading
                                              → unified_scoring → collection_fusion
                                              → verification ──[valid_count>0 or retried]──> classification → answer_generation → END
                                                             ──[valid_count==0 and retry_count<1]──> unified_scoring (retry, ≤1 次)
                       ──[is_job_query=False]─> reject → END

Nodes:
  1. query_understanding  — LLM extracts structured preferences AND classifies intent
  2. query_expansion      — expand keywords/tags via QueryExpander
  3. candidate_loading    — load jobs from MySQL with hard filters
  4. unified_scoring      — TF-IDF/BM25/Dense/RRF 检索 + 可选 LLM 精排 + ScoringEngine 多字段打分
  5. collection_fusion    — normalize scores across sources, top-K
  6. verification         — 标 valid/rejected/unknown；0 个 valid 时触发一次重试（换检索策略，不放宽硬条件）
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
# 受约束 Planner：query_understanding 输出的 retrieval_mode → 具体检索配置
# ---------------------------------------------------------------------------

_PLANNER_MODE_MAP = {
    # 精确技术词/明确技能 → 纯 BM25 词面匹配，不需要 dense 的模糊语义，也不
    # 需要精排（避免 dense 把概念相近、实际职责不同的职位召回进来）。
    "exact": {"ir_mode": "bm25", "use_reranker": False},
    # 职责性描述、关键词不一定和职位原文重合 → BM25+Dense 按 RRF 融合。
    "semantic": {"ir_mode": "hybrid_rrf", "use_reranker": False},
    # 查询本身信息量很少 → 在 semantic 基础上加精排，多一层判断弥补检索信号不足。
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
    """tfidf_model.pkl 是 python -m src.ir.tfidf 训练的，pickle 里 tokenizer 引用
    __main__.JobIRSystem。任何非 src.ir.tfidf 入口加载都会报 AttributeError，
    临时把类注入当前 __main__ 兜住。
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

    有 session_id 时和历史记忆合并（本轮明确提到的字段覆盖记忆，本轮没提的
    字段回退记忆）。只有"真正冷启动+合并后仍然完全没有可用信号"才反问——
    exploratory 模式（步骤④）本身就是为了应付模糊查询设计的，不能一模糊就
    反问，否则前面步骤白做。
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
        save_memory(session_id, prefs)  # 存合并后最新的完整画像

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
    """信息完全不足时反问，而不是瞎猜——只在真正冷启动+全空时触发。"""
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

    # 受约束 Planner：query_understanding 已经判断过这条查询该用哪种检索
    # 策略（exact/semantic/exploratory），这里映射成具体的 ir_mode/reranker
    # 组合。显式传入的 config 优先于 Planner 的自动选择（CLI 调试、
    # src/eval/* 的 ablation 配置都不受影响，行为和之前完全一致）。
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
        # BM25（词面）+ Dense（语义）按名次做 RRF，而非原始分数加权平均——
        # 两路分数尺度不同，直接平均会被尺度大的一路主导。
        bm25_s = _get_bm25_system().get_similarities(text_query)
        dense_s = _get_dense_system().get_similarities(text_query)
        fused = reciprocal_rank_fusion([bm25_s, dense_s])
        # RRF 原始值量级很小（两路时最大约 2/(k+1)），必须重新 min-max 到 [0,1]
        # 才能和 ScoringEngine 里其他字段（薪资/地点/标签…）的量级对齐；否则
        # description 权重（默认最大，0.35）会被其他字段完全淹没，hybrid_rrf
        # 等于没在按文本相关性排序。
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
        # 对粗分 Top-N 做更细致的 query-职位相关性判断，重新打分覆盖粗分；
        # 用原始 user_query 而非可能被 query_expansion 展开过的 text_query，
        # 因为要判断的是"是否满足用户原话意图"，不是关键词匹配。
        ranked_candidates = sorted(
            state["candidates"], key=lambda j: text_scores.get(j["job_id"], 0.0), reverse=True
        )
        reranked = rerank(state["user_query"], ranked_candidates, api_key=state.get("api_key"))
        text_scores.update(reranked)  # 只覆盖被精排到的 Top-N，其余保留原粗分

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

    dedupe=True: HN 月度帖会让同一岗位以多 job_id 入库，按 (company, title) 去重。
    pool_eval 不调用此节点（自己平铺评估 12 配置），评估数字不受影响。
    """
    top_k = state.get("top_k") or 10
    ranked = fuse_and_rank(state["scored_jobs"], top_k=top_k, dedupe=True)
    return {"ranked_jobs": ranked}


def node_verification(state: PipelineState) -> dict:
    """校验 ranked_jobs，标 valid/rejected/unknown；valid 数为 0 且还没重试过
    时触发一次重试（换更强的检索策略，不碰 hard_filters，不放宽硬条件）。
    """
    jobs = verify_jobs(state["ranked_jobs"], state["preferences"], state["user_query"])
    valid_count = sum(1 for j in jobs if j["verification_status"] == "valid")
    retry_count = state.get("retry_count", 0)
    verified = [j for j in jobs if j["verification_status"] != "rejected"]

    if valid_count == 0 and retry_count < 1:
        # 广播式加强：换成目前能力最强的检索组合。如果这一轮本来就已经是
        # hybrid_rrf+rerank，这次重试不会有实质变化——这是已知的局限，
        # vNext 只要求"最多重试一次"，不保证重试一定有效。
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
        session_id: 跨轮偏好记忆用的会话标识；None 时行为等同单轮无状态

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
        description="跑一次完整 pipeline（冒烟测试用）"
    )
    parser.add_argument("query", nargs="+", help="自然语言查询")
    parser.add_argument(
        "--ir-mode",
        choices=["tfidf", "bm25", "dense", "hybrid", "hybrid_rrf"],
        default=None,
        help="检索模式，不传则用默认（tfidf）",
    )
    parser.add_argument(
        "--rerank", action="store_true",
        help="对 Top-N 粗分候选做 LLM 精排",
    )
    parser.add_argument(
        "--session", default=None,
        help="会话ID，跨次调用共享偏好记忆（多次用同一个 id 模拟多轮对话）",
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    config = {}
    if args.ir_mode:
        config["ir_mode"] = args.ir_mode
    if args.rerank:
        config["use_reranker"] = True

    print(f"查询: {query}\n")
    result = run_pipeline(query, config=config, session_id=args.session)
    print(f"回答:\n{result.get('answer', '无回答')}")
