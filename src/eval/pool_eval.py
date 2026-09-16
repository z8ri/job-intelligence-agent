"""
Pooled evaluation pipeline: Phase A (ranking) → Phase B (LLM pool annotation) → Phase C (metrics).

This replaces the broken main flow in ablation.py / run_eval.py / annotate.py:
  - old ablation.run_single_config ignored ranked_jobs and computed metrics
    directly on annotations, so every config scored identically.
  - old annotate.py asked the user to grade unsorted DB rows — that is not pooling.
  - old run_eval.py refused to run without annotations, but annotations cannot
    exist until at least one ranking is produced. Chicken-and-egg.

New flow:
  Phase A — for each query, parse preferences ONCE via LLM, then for each of the
            10 ablation configs run the pipeline's non-LLM nodes (expansion,
            candidate loading, scoring, fusion) to produce a top-10 ranking.
            Preferences are cached; rankings are cached.
  Phase B — pool top-10 from all configs per query (≈20–50 jobs/query), rate each
            (query, job) pair with gpt-4o-mini on a 0/1/2 scale. Annotations
            cached so re-runs don't re-call the LLM.
  Phase C — for each config, map its ranked job_ids to pool grades and compute
            P@5, P@10, nDCG@5, nDCG@10 averaged across queries. Emit JSON + md.

Usage:
    python -m src.eval.pool_eval phase_a            # run rankings (no LLM cost)
    python -m src.eval.pool_eval phase_b            # annotate pool via LLM (~$0.15)
    python -m src.eval.pool_eval phase_c            # compute metrics + table
    python -m src.eval.pool_eval all                # A → B → C
    python -m src.eval.pool_eval pool_stats         # just show pool sizes after A
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

from src.eval import PROJECT_ROOT, load_test_queries
from src.eval.ablation import ABLATION_CONFIGS
from src.eval.metrics import compute_all_metrics, average_metrics
from src.db.database import load_candidates
from src.scoring.fusion import fuse_and_rank
from src.ir.query_expansion import QueryExpander
from src.ir.tfidf import JobIRSystem
from src.ir.bm25 import JobBM25System
from src.ir.dense import JobDenseSystem
from src.ir.rrf import reciprocal_rank_fusion
from src.scoring.engine import ScoringEngine
from src.scoring.reranker import rerank
from src.llm.query_understanding import parse_preferences
from src.llm import MODEL, get_client


import os

# 允许通过环境变量临时把产物重定向到另一个目录（例如跑 vNext 新增 config
# 时不想覆盖已交付报告引用的历史结果），默认行为完全不变。
RESULTS_DIR = Path(os.environ.get("POOL_EVAL_RESULTS_DIR") or (PROJECT_ROOT / "data" / "eval_results"))
PREF_CACHE_PATH = RESULTS_DIR / "preferences_cache.json"
RANKINGS_PATH = RESULTS_DIR / "rankings.json"
POOL_PATH = RESULTS_DIR / "pool_annotations.json"
METRICS_JSON_PATH = RESULTS_DIR / "metrics.json"
METRICS_MD_PATH = RESULTS_DIR / "metrics_table.md"

TOP_K = 10
K_VALUES = [5, 10]

# Maps engine scoring field → preference key that activates it
FIELD_TO_PREF = {
    "description": "description_keywords",
    "salary":      "target_salary",
    "location":    "preferred_location",
    "remote":      "remote_preference",
    "tags":        "desired_tags",
    "category":    "preferred_category",
}


# ---------------------------------------------------------------------------
# Config materialization: rewrite (prefs, weight_adj) per ablation config
# ---------------------------------------------------------------------------

def apply_config_to_prefs(
    preferences: dict,
    weight_adjustments: dict,
    config: dict,
) -> tuple[dict, dict, set[str]]:
    """
    Translate an ablation config into (prefs, weight_adj, active_fields_set).

    - active_fields == "all" → keep prefs as-is.
    - active_fields is a list → zero out pref keys for fields NOT in the list
      so ScoringEngine.compute_final_score won't activate them.
    - use_category=False → drop preferred_category regardless of active_fields.
    - force_default_weights=True → drop all weight_adjustments.

    Returns:
        prefs_copy, weight_adj_copy, active_fields as a set like {"description","salary",...}
    """
    prefs = copy.deepcopy(preferences) if preferences else {}
    w_adj = dict(weight_adjustments or {})

    active_cfg = config.get("active_fields", "all")
    if active_cfg == "all":
        active = set(FIELD_TO_PREF.keys())
    else:
        active = set(active_cfg)

    # active_fields 已交给 engine 控制激活，这里再把对应 pref 置 None 是双保险，
    # 对默认行为无副作用。
    for fld, pref_key in FIELD_TO_PREF.items():
        if fld == "description":
            continue
        if fld not in active:
            prefs[pref_key] = None

    if not config.get("use_category", True):
        prefs["preferred_category"] = None
        active.discard("category")

    if config.get("force_default_weights"):
        w_adj = {}

    return prefs, w_adj, active


def apply_hard_filters_in_python(candidates: list[dict], preferences: dict) -> list[dict]:
    """
    Baseline comparator: convert every structured preference into a boolean
    must-match filter (the rigid baseline this project compares against). Runs in
    Python over the loaded candidates so we don't need to touch SQL.

    For hard_filter_baseline:
      - remote_preference → exact job.remote match
      - preferred_category → exact job.category match
      - preferred_location → substring match in job.location
      - target_salary → target must lie in [salary_min, salary_max]
      - desired_tags → at least one tag in job.tags (soft intersection;
        stricter AND-match would empty the pool for common queries)
    """
    target = preferences.get("target_salary")
    loc = (preferences.get("preferred_location") or "").strip().lower()
    rem = preferences.get("remote_preference")
    cat = preferences.get("preferred_category")
    tags = {t.lower() for t in (preferences.get("desired_tags") or [])}

    out = []
    for job in candidates:
        if rem and job.get("remote") and job["remote"] != rem:
            continue
        if cat and job.get("category") and job["category"] != cat:
            continue
        if loc:
            job_loc = (job.get("location") or "").lower()
            if loc not in job_loc:
                continue
        if target:
            s_min = job.get("salary_min")
            s_max = job.get("salary_max")
            if s_min is not None and s_max is not None:
                if not (s_min <= target <= s_max):
                    continue
            # if salary missing, don't exclude — let text ranking surface it
        if tags:
            job_tags = {t.lower() for t in (job.get("tags") or [])}
            if not (tags & job_tags):
                continue
        out.append(job)
    return out


# ---------------------------------------------------------------------------
# Scoring a single (job, config) without LangGraph
# ---------------------------------------------------------------------------

def score_one_job(
    job: dict,
    prefs: dict,
    weight_adj: dict,
    tfidf_score: float,
    active: set[str],
    config: dict,
    engine: ScoringEngine,
) -> float:
    """Return the final score for one job under one config."""
    final, breakdown = engine.compute_final_score(
        job, prefs, tfidf_score, weight_adjustments=weight_adj, active_fields=active,
    )

    if config.get("equal_weights") and breakdown:
        final = round(sum(breakdown.values()) / len(breakdown), 4)

    return final


# ---------------------------------------------------------------------------
# Phase A — rankings
# ---------------------------------------------------------------------------

def _load_or_init(path: Path, default):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return default


def _save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def cache_preferences(queries: list[dict], force: bool = False) -> dict:
    """Parse preferences for every query via LLM and cache to disk."""
    cache = {} if force else _load_or_init(PREF_CACHE_PATH, {})
    missing = [q for q in queries if q["id"] not in cache]
    if not missing:
        print(f"[pref-cache] 40/40 命中，跳过 LLM 调用")
        return cache

    print(f"[pref-cache] 需要调用 LLM {len(missing)} 次（gpt-4o-mini）")
    for q in missing:
        try:
            result = parse_preferences(q["query"])
            cache[q["id"]] = {
                "preferences": result["preferences"],
                "weights": result["weights"],
            }
            print(f"  [{q['id']}] ok")
        except Exception as e:
            print(f"  [{q['id']}] 失败: {e}")
        _save_json(PREF_CACHE_PATH, cache)  # incremental save

    return cache


def run_phase_a(queries: list[dict], force: bool = False) -> dict:
    """
    Produce rankings[config_name][qid] = [job_id, ...] of length up to TOP_K.
    Preferences come from cache_preferences().
    """
    if RANKINGS_PATH.exists() and not force:
        print(f"[phase-a] 已有 rankings.json，使用 --force-a 覆盖")
        return _load_or_init(RANKINGS_PATH, {})

    pref_cache = cache_preferences(queries)

    print("[phase-a] 加载候选全量 + TF-IDF + BM25 + ScoringEngine ...")
    all_candidates = load_candidates()
    print(f"  候选数: {len(all_candidates)}")

    ir = JobIRSystem()
    # pickle was saved with __main__.JobIRSystem; expose the class under
    # __main__ so unpickling succeeds in this entrypoint too.
    import __main__
    if not hasattr(__main__, "JobIRSystem"):
        __main__.JobIRSystem = JobIRSystem
    ir.load_model()

    bm25_needed = any(
        (cfg.get("ir_mode") or "tfidf") in ("bm25", "hybrid", "hybrid_rrf")
        for cfg in ABLATION_CONFIGS.values()
    )
    bm25: JobBM25System | None = None
    if bm25_needed:
        bm25 = JobBM25System()
        bm25.load_model()

    dense_needed = any(
        (cfg.get("ir_mode") or "tfidf") in ("dense", "hybrid_rrf")
        for cfg in ABLATION_CONFIGS.values()
    )
    dense: JobDenseSystem | None = None
    if dense_needed:
        dense = JobDenseSystem()
        dense.load_model()

    engine = ScoringEngine()
    expander = QueryExpander()

    rankings: dict[str, dict[str, list[str]]] = {cfg: {} for cfg in ABLATION_CONFIGS}

    for q in queries:
        qid = q["id"]
        if qid not in pref_cache:
            print(f"  [{qid}] 缺少 preferences，跳过")
            continue
        prefs_base = pref_cache[qid]["preferences"]
        w_adj_base = prefs_base.get("weight_adjustments") or {}

        for cfg_name, cfg in ABLATION_CONFIGS.items():
            prefs, w_adj, active = apply_config_to_prefs(prefs_base, w_adj_base, cfg)

            # expansion
            if not cfg.get("skip_expansion"):
                exp_kw, exp_tags = expander.expand_query(
                    prefs.get("description_keywords"), prefs.get("desired_tags"),
                )
            else:
                exp_kw = prefs.get("description_keywords") or []
                exp_tags = prefs.get("desired_tags") or []

            # text query: prefer expanded keywords; fall back to raw query
            text_query = " ".join(exp_kw) if exp_kw else q["query"]
            ir_mode = (cfg.get("ir_mode") or "tfidf").lower()
            if ir_mode == "bm25":
                text_scores = bm25.get_similarities(text_query)
            elif ir_mode == "dense":
                text_scores = dense.get_similarities(text_query)
            elif ir_mode == "hybrid":
                tfidf_s = ir.get_similarities(text_query)
                bm25_s = bm25.get_similarities(text_query)
                text_scores = {
                    jid: 0.5 * tfidf_s.get(jid, 0.0) + 0.5 * bm25_s.get(jid, 0.0)
                    for jid in set(tfidf_s) | set(bm25_s)
                }
            elif ir_mode == "hybrid_rrf":
                # 镜像 src/pipeline/graph.py::node_unified_scoring 的写法，
                # 包括 RRF 融合后必须重新 min-max 归一化到 [0,1] 这一步——
                # 漏掉这步会让 description 权重被其他字段淹没（之前在
                # graph.py 上踩过这个坑）。
                bm25_s = bm25.get_similarities(text_query)
                dense_s = dense.get_similarities(text_query)
                fused = reciprocal_rank_fusion([bm25_s, dense_s])
                if fused:
                    f_min, f_max = min(fused.values()), max(fused.values())
                    if f_max > f_min:
                        text_scores = {jid: (s - f_min) / (f_max - f_min) for jid, s in fused.items()}
                    else:
                        text_scores = {jid: 0.0 for jid in fused}
                else:
                    text_scores = {}
            else:
                text_scores = ir.get_similarities(text_query)

            # candidate pool (hard filter baseline narrows here)
            if cfg.get("hard_filter_mode"):
                pool = apply_hard_filters_in_python(all_candidates, prefs_base)
            else:
                pool = all_candidates

            if cfg.get("use_reranker"):
                ranked_candidates = sorted(
                    pool, key=lambda j: text_scores.get(j["job_id"], 0.0), reverse=True
                )
                reranked = rerank(q["query"], ranked_candidates)
                text_scores.update(reranked)

            scored = []
            for job in pool:
                tfidf = text_scores.get(job["job_id"], 0.0)
                if cfg.get("hard_filter_mode"):
                    # Survivors ranked purely by description score (the
                    # "硬过滤基线" baseline — no soft scoring).
                    final = round(float(tfidf), 4)
                else:
                    final = score_one_job(job, prefs, w_adj, tfidf, active, cfg, engine)
                j = dict(job)
                j["final_score"] = final
                scored.append(j)

            ranked = fuse_and_rank(scored, top_k=TOP_K)
            rankings[cfg_name][qid] = [j["job_id"] for j in ranked]

        print(f"  [{qid}] done — {len(ABLATION_CONFIGS)} configs × top-{TOP_K}")

    _save_json(RANKINGS_PATH, rankings)
    print(f"[phase-a] 已写入 {RANKINGS_PATH}")
    return rankings


# ---------------------------------------------------------------------------
# Phase B — pool annotation via LLM
# ---------------------------------------------------------------------------

POOL_SYSTEM_PROMPT = """\
You rate job-posting relevance to a user's job-search query on a 3-point scale.

Scale:
  0 = NOT relevant: wrong role type, missing critical explicit requirements, or major mismatch.
  1 = PARTIALLY relevant: matches some criteria but misses key explicit requirements (e.g. wrong location, salary below target, wrong remote/onsite mode).
  2 = HIGHLY relevant: matches the key explicit criteria the user stated (minor mismatches acceptable).

Guidelines:
  - Only judge against what the user EXPLICITLY stated. Do not penalize unstated dimensions.
  - Missing data (e.g. salary unknown) is neutral — not a disqualifier unless the user said it's required.
  - Wrong category (e.g. user wants backend, job is frontend) → 0.
  - Right role but significant location/salary mismatch → 1.
  - Salary offered < target by ≤20% → still 1 or 2 depending on other matches.

Respond with ONLY one character: the digit 0, 1, or 2. No explanation."""


def _job_snippet(job: dict, max_desc_chars: int = 600) -> str:
    """Format a job row for the LLM annotator."""
    sal = ""
    s_min = job.get("salary_min")
    s_max = job.get("salary_max")
    if s_min and s_max:
        sal = f"${s_min:,}-${s_max:,}"
    elif s_min:
        sal = f"${s_min:,}+"
    elif s_max:
        sal = f"up to ${s_max:,}"
    else:
        sal = "unknown"

    tags = ", ".join(job.get("tags") or []) or "none listed"
    desc = (job.get("description") or "").strip().replace("\n", " ")
    if len(desc) > max_desc_chars:
        desc = desc[:max_desc_chars] + "..."

    return (
        f"Title: {job.get('title') or 'unknown'}\n"
        f"Company: {job.get('company') or 'unknown'}\n"
        f"Location: {job.get('location') or 'unknown'}\n"
        f"Remote mode: {job.get('remote') or 'unknown'}\n"
        f"Salary: {sal}\n"
        f"Category: {job.get('category') or 'unknown'}\n"
        f"Tags: {tags}\n"
        f"Description: {desc}"
    )


def build_pool(rankings: dict, top_k: int = TOP_K) -> dict[str, list[str]]:
    """For each query, return the union of top-K job_ids across all configs."""
    pool: dict[str, set[str]] = {}
    for cfg_name, per_query in rankings.items():
        for qid, job_ids in per_query.items():
            pool.setdefault(qid, set()).update(job_ids[:top_k])
    return {qid: sorted(ids) for qid, ids in pool.items()}


def _rate_one(client, query_text: str, job: dict) -> int | None:
    """Call LLM to rate one (query, job) pair. Return 0/1/2 or None on failure."""
    messages = [
        {"role": "system", "content": POOL_SYSTEM_PROMPT},
        {"role": "user", "content": f"User query:\n  {query_text}\n\nJob posting:\n{_job_snippet(job)}\n\nRating (0, 1, or 2):"},
    ]
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=4,
            )
            raw = (resp.choices[0].message.content or "").strip()
            # grab first digit
            for ch in raw:
                if ch in "012":
                    return int(ch)
        except Exception as e:
            print(f"    LLM error (attempt {attempt+1}): {e}")
            time.sleep(1.5)
    return None


def run_phase_b(queries: list[dict], force: bool = False) -> dict:
    """Annotate the pool. Cache per (qid, job_id)."""
    rankings = _load_or_init(RANKINGS_PATH, None)
    if rankings is None:
        print("[phase-b] 缺 rankings.json，请先跑 phase_a")
        sys.exit(1)

    pool = build_pool(rankings)
    total = sum(len(ids) for ids in pool.values())
    print(f"[phase-b] 池大小: {len(pool)} 查询 × 平均 {total / max(1,len(pool)):.1f} job = {total} 条待标注")

    annotations = {} if force else _load_or_init(POOL_PATH, {})

    # Build qid → query text map and job_id → job dict map
    qtext = {q["id"]: q["query"] for q in queries}

    print("[phase-b] 加载候选池（用于构造标注用的 job 描述）...")
    all_candidates = load_candidates()
    job_by_id = {j["job_id"]: j for j in all_candidates}

    client = get_client()
    pending = 0
    done = 0
    for qid, job_ids in pool.items():
        for jid in job_ids:
            if qid in annotations and jid in annotations[qid]:
                continue
            pending += 1

    print(f"[phase-b] 需要新增标注 {pending} 条（gpt-4o-mini）")
    if pending == 0:
        return annotations

    for qid, job_ids in pool.items():
        annotations.setdefault(qid, {})
        for jid in job_ids:
            if jid in annotations[qid]:
                continue
            job = job_by_id.get(jid)
            if job is None:
                print(f"    [{qid}/{jid}] 库中找不到该 job，记 0")
                annotations[qid][jid] = 0
                continue
            grade = _rate_one(client, qtext[qid], job)
            if grade is None:
                print(f"    [{qid}/{jid}] 标注失败 → 记 0（保守）")
                grade = 0
            annotations[qid][jid] = grade
            done += 1
            if done % 20 == 0:
                print(f"    进度 {done}/{pending}")
                _save_json(POOL_PATH, annotations)
        _save_json(POOL_PATH, annotations)

    _save_json(POOL_PATH, annotations)
    print(f"[phase-b] 完成 {done} 条新标注 → {POOL_PATH}")
    return annotations


# ---------------------------------------------------------------------------
# Phase C — metrics + markdown table
# ---------------------------------------------------------------------------

def run_phase_c() -> dict:
    rankings = _load_or_init(RANKINGS_PATH, None)
    annotations = _load_or_init(POOL_PATH, None)
    if rankings is None or annotations is None:
        print("[phase-c] 需要 rankings.json 和 pool_annotations.json 都就绪")
        sys.exit(1)

    per_config: dict[str, dict] = {}

    for cfg_name, per_query in rankings.items():
        per_query_metrics = []
        for qid, job_ids in per_query.items():
            # Jobs not in the pool are assumed 0 (not surfaced by any config).
            # This is the standard pooled evaluation assumption.
            grades = [annotations.get(qid, {}).get(jid, 0) for jid in job_ids]
            m = compute_all_metrics(grades, K_VALUES)
            m["query_id"] = qid
            per_query_metrics.append(m)

        avg = average_metrics(per_query_metrics)
        per_config[cfg_name] = {
            "description": ABLATION_CONFIGS[cfg_name].get("description", ""),
            "average": avg,
            "per_query": per_query_metrics,
        }

    _save_json(METRICS_JSON_PATH, per_config)

    # markdown table
    header = "| Config | P@5 | P@10 | nDCG@5 | nDCG@10 | Description |"
    sep =    "|--------|-----|------|--------|---------|-------------|"
    lines = [header, sep]
    for name, res in per_config.items():
        a = res["average"]
        lines.append(
            f"| {name} | {a.get('P@5',0):.3f} | {a.get('P@10',0):.3f} | "
            f"{a.get('nDCG@5',0):.3f} | {a.get('nDCG@10',0):.3f} | {res['description']} |"
        )
    table = "\n".join(lines)
    METRICS_MD_PATH.write_text(table + "\n", encoding="utf-8")
    print(table)
    print(f"\n[phase-c] metrics.json → {METRICS_JSON_PATH}")
    print(f"[phase-c] table.md    → {METRICS_MD_PATH}")
    return per_config


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def show_pool_stats() -> None:
    rankings = _load_or_init(RANKINGS_PATH, None)
    if rankings is None:
        print("rankings.json 不存在")
        return
    pool = build_pool(rankings)
    sizes = [len(v) for v in pool.values()]
    if not sizes:
        print("空池")
        return
    print(f"queries: {len(sizes)}")
    print(f"pool size per query: min={min(sizes)} max={max(sizes)} mean={sum(sizes)/len(sizes):.1f}")
    print(f"total annotations needed: {sum(sizes)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["phase_a", "phase_b", "phase_c", "all", "pool_stats"])
    parser.add_argument("--force-a", action="store_true", help="rerun Phase A, overwrite rankings.json")
    parser.add_argument("--force-b", action="store_true", help="rerun Phase B, ignore cached annotations")
    args = parser.parse_args()

    queries = load_test_queries()

    if args.phase == "phase_a":
        run_phase_a(queries, force=args.force_a)
    elif args.phase == "phase_b":
        run_phase_b(queries, force=args.force_b)
    elif args.phase == "phase_c":
        run_phase_c()
    elif args.phase == "pool_stats":
        show_pool_stats()
    elif args.phase == "all":
        run_phase_a(queries, force=args.force_a)
        run_phase_b(queries, force=args.force_b)
        run_phase_c()


if __name__ == "__main__":
    main()
