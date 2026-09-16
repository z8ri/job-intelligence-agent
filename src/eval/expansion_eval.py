"""
§7.4 Query Expansion 单独评估：在 18 条缩写敏感查询上对比 with/without expansion。

与 pool_eval.py 的差别：
  - 测试集独立（test_queries_expansion.json，18 条 vs 40 条）
  - 只跑两档配置：with_expansion / no_expansion（其余 flag 沿用 §7.7 baseline）
  - 缓存路径全部独立（expansion_*.json），禁止污染 §7.7 主数字
  - 增加 expansion_hit_rate 指标（扩展词在 top-10 文档命中率）

复用 pool_eval 的：apply_config_to_prefs / score_one_job / build_pool / _rate_one /
_job_snippet / POOL_SYSTEM_PROMPT / _load_or_init / _save_json。

Usage:
    python -m src.eval.expansion_eval phase_a       # 排序（无 LLM 成本）
    python -m src.eval.expansion_eval phase_b       # 池标注（gpt-4o-mini，~$0.05）
    python -m src.eval.expansion_eval phase_c       # 指标 + hit_rate + 报告
    python -m src.eval.expansion_eval all           # A → B → C
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from src.eval import PROJECT_ROOT
from src.eval.metrics import compute_all_metrics, average_metrics
from src.eval.pool_eval import (
    apply_config_to_prefs,
    score_one_job,
    build_pool,
    _rate_one,
    _job_snippet,
    _load_or_init,
    _save_json,
    TOP_K,
    K_VALUES,
)
from src.db.database import load_candidates
from src.scoring.fusion import fuse_and_rank
from src.ir.query_expansion import QueryExpander
from src.ir.tfidf import JobIRSystem
from src.scoring.engine import ScoringEngine
from src.llm.query_understanding import parse_preferences
from src.llm import get_client


# ---------------------------------------------------------------------------
# 独立路径常量 — 严禁 import pool_eval 的同名常量
# ---------------------------------------------------------------------------
RESULTS_DIR = PROJECT_ROOT / "data" / "eval_results"
QUERIES_PATH = PROJECT_ROOT / "data" / "test_queries_expansion.json"
PREF_CACHE_PATH = RESULTS_DIR / "expansion_preferences_cache.json"
RANKINGS_PATH = RESULTS_DIR / "expansion_rankings.json"
POOL_PATH = RESULTS_DIR / "expansion_pool_annotations.json"
METRICS_JSON_PATH = RESULTS_DIR / "expansion_metrics.json"
METRICS_MD_PATH = RESULTS_DIR / "expansion_metrics_table.md"

# 两档配置：除 skip_expansion 外其余 flag 与 §7.7 baseline 一致
EXPANSION_CONFIGS = {
    "no_expansion": {
        "description": "Query expansion disabled (baseline)",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": True,
        "use_category": True,
        "hard_filter_mode": False,
        "ir_mode": "tfidf",
    },
    "with_expansion": {
        "description": "Query expansion enabled (synonyms + tag hierarchy)",
        "active_fields": "all",
        "equal_weights": False,
        "skip_expansion": False,
        "use_category": True,
        "hard_filter_mode": False,
        "ir_mode": "tfidf",
    },
}


# ---------------------------------------------------------------------------
# 测试集加载
# ---------------------------------------------------------------------------

def load_expansion_queries() -> list[dict]:
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Pref 缓存（本地路径）
# ---------------------------------------------------------------------------

def cache_preferences(queries: list[dict], force: bool = False) -> dict:
    cache = {} if force else _load_or_init(PREF_CACHE_PATH, {})
    missing = [q for q in queries if q["id"] not in cache]
    if not missing:
        print(f"[pref-cache] {len(queries)}/{len(queries)} 命中，跳过 LLM 调用")
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
        _save_json(PREF_CACHE_PATH, cache)
    return cache


# ---------------------------------------------------------------------------
# Phase A — 两档排序
# ---------------------------------------------------------------------------

def run_phase_a(queries: list[dict], force: bool = False) -> dict:
    if RANKINGS_PATH.exists() and not force:
        print(f"[phase-a] 已有 {RANKINGS_PATH.name}，使用 --force-a 覆盖")
        return _load_or_init(RANKINGS_PATH, {})

    pref_cache = cache_preferences(queries)

    print("[phase-a] 加载候选 + TF-IDF + ScoringEngine ...")
    all_candidates = load_candidates()
    print(f"  候选数: {len(all_candidates)}")

    ir = JobIRSystem()
    import __main__
    if not hasattr(__main__, "JobIRSystem"):
        __main__.JobIRSystem = JobIRSystem
    ir.load_model()

    engine = ScoringEngine()
    expander = QueryExpander()

    rankings: dict[str, dict[str, list[str]]] = {cfg: {} for cfg in EXPANSION_CONFIGS}

    for q in queries:
        qid = q["id"]
        if qid not in pref_cache:
            print(f"  [{qid}] 缺 preferences，跳过")
            continue
        prefs_base = pref_cache[qid]["preferences"]
        w_adj_base = prefs_base.get("weight_adjustments") or {}

        for cfg_name, cfg in EXPANSION_CONFIGS.items():
            prefs, w_adj, active = apply_config_to_prefs(prefs_base, w_adj_base, cfg)

            if not cfg.get("skip_expansion"):
                exp_kw, exp_tags = expander.expand_query(
                    prefs.get("description_keywords"), prefs.get("desired_tags"),
                )
            else:
                exp_kw = prefs.get("description_keywords") or []
                exp_tags = prefs.get("desired_tags") or []

            text_query = " ".join(exp_kw) if exp_kw else q["query"]
            text_scores = ir.get_similarities(text_query)

            scored = []
            for job in all_candidates:
                tfidf = text_scores.get(job["job_id"], 0.0)
                final = score_one_job(job, prefs, w_adj, tfidf, active, cfg, engine)
                j = dict(job)
                j["final_score"] = final
                scored.append(j)

            ranked = fuse_and_rank(scored, top_k=TOP_K)
            rankings[cfg_name][qid] = [j["job_id"] for j in ranked]

        # 自检：两档 top-10 不应完全一致
        a = rankings["no_expansion"].get(qid, [])
        b = rankings["with_expansion"].get(qid, [])
        same = "(IDENTICAL — 警告)" if a == b else f"(diff={len(set(a) ^ set(b))})"
        print(f"  [{qid}] done {same}")

    _save_json(RANKINGS_PATH, rankings)
    print(f"[phase-a] 已写入 {RANKINGS_PATH}")
    return rankings


# ---------------------------------------------------------------------------
# Phase B — 池化 LLM 标注（本地路径）
# ---------------------------------------------------------------------------

def run_phase_b(queries: list[dict], force: bool = False) -> dict:
    rankings = _load_or_init(RANKINGS_PATH, None)
    if rankings is None:
        print("[phase-b] 缺 rankings，请先跑 phase_a")
        sys.exit(1)

    pool = build_pool(rankings)
    total = sum(len(ids) for ids in pool.values())
    print(f"[phase-b] 池大小: {len(pool)} 查询 × 平均 {total / max(1,len(pool)):.1f} job = {total} 条待标注")

    if total > 500:
        print(f"[phase-b] 标注总数 {total} > 500，超出预算守门，停止。请先精简测试集或排查 phase_a 异常")
        sys.exit(1)

    annotations = {} if force else _load_or_init(POOL_PATH, {})
    qtext = {q["id"]: q["query"] for q in queries}

    print("[phase-b] 加载候选池（构造标注用 job 描述）...")
    all_candidates = load_candidates()
    job_by_id = {j["job_id"]: j for j in all_candidates}

    client = get_client()
    pending = sum(
        1
        for qid, ids in pool.items()
        for jid in ids
        if not (qid in annotations and jid in annotations[qid])
    )
    print(f"[phase-b] 需要新增标注 {pending} 条（gpt-4o-mini）")
    if pending == 0:
        return annotations

    done = 0
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
# Expansion hit rate
# ---------------------------------------------------------------------------

def expansion_hit_rate(prefs: dict, top10_jobs: list[dict], expander: QueryExpander) -> dict:
    """
    扩展命中率：扩展后新增的关键词/标签在 top-10 文档（description ∪ tags ∪ title）的覆盖比例。

    Returns:
        {
          "kw_hit_rate":  float | None,   # 新增 keywords 中命中的比例（None 表示无新增词）
          "tag_hit_rate": float | None,
          "new_kw_count": int,
          "new_tag_count": int,
          "new_kw_hit_list": [str],       # 命中的扩展 keyword
          "new_tag_hit_list": [str],
        }
    """
    base_kw = {(w or "").lower() for w in (prefs.get("description_keywords") or [])}
    base_tag = {(w or "").lower() for w in (prefs.get("desired_tags") or [])}
    exp_kw, exp_tag = expander.expand_query(
        list(base_kw), list(base_tag)
    )
    new_kw = {(w or "").lower() for w in exp_kw} - base_kw
    new_tag = {(w or "").lower() for w in exp_tag} - base_tag

    text = " ".join(
        (
            (j.get("description") or "")
            + " "
            + " ".join(j.get("tags") or [])
            + " "
            + (j.get("title") or "")
        ).lower()
        for j in top10_jobs
    )

    kw_hits = sorted(w for w in new_kw if w and w in text)
    tag_hits = sorted(w for w in new_tag if w and w in text)

    return {
        "kw_hit_rate": (len(kw_hits) / len(new_kw)) if new_kw else None,
        "tag_hit_rate": (len(tag_hits) / len(new_tag)) if new_tag else None,
        "new_kw_count": len(new_kw),
        "new_tag_count": len(new_tag),
        "new_kw_hit_list": kw_hits,
        "new_tag_hit_list": tag_hits,
    }


def _avg_optional(values: list) -> float | None:
    """Mean ignoring None."""
    xs = [v for v in values if v is not None]
    return sum(xs) / len(xs) if xs else None


# ---------------------------------------------------------------------------
# Phase C — 指标 + hit_rate + 表格
# ---------------------------------------------------------------------------

def run_phase_c() -> dict:
    rankings = _load_or_init(RANKINGS_PATH, None)
    annotations = _load_or_init(POOL_PATH, None)
    if rankings is None or annotations is None:
        print("[phase-c] 需要 rankings + pool_annotations 都就绪")
        sys.exit(1)

    queries = load_expansion_queries()
    pref_cache = _load_or_init(PREF_CACHE_PATH, {})

    print("[phase-c] 加载候选池构造 hit_rate ...")
    all_candidates = load_candidates()
    job_by_id = {j["job_id"]: j for j in all_candidates}
    expander = QueryExpander()

    per_config: dict[str, dict] = {}

    for cfg_name, per_query in rankings.items():
        per_query_metrics = []
        per_query_hit = []
        for q in queries:
            qid = q["id"]
            job_ids = per_query.get(qid, [])
            if not job_ids:
                continue
            grades = [annotations.get(qid, {}).get(jid, 0) for jid in job_ids]
            m = compute_all_metrics(grades, K_VALUES)
            m["query_id"] = qid
            per_query_metrics.append(m)

            # hit_rate 仅 with_expansion 配置算（no_expansion 没有"扩展"行为）
            if cfg_name == "with_expansion" and qid in pref_cache:
                top10 = [job_by_id[jid] for jid in job_ids[:10] if jid in job_by_id]
                hit = expansion_hit_rate(pref_cache[qid]["preferences"], top10, expander)
                hit["query_id"] = qid
                per_query_hit.append(hit)

        avg = average_metrics(per_query_metrics)
        per_config[cfg_name] = {
            "description": EXPANSION_CONFIGS[cfg_name]["description"],
            "average": avg,
            "per_query": per_query_metrics,
        }
        if cfg_name == "with_expansion":
            per_config[cfg_name]["hit_rate"] = {
                "avg_kw_hit_rate": _avg_optional([h["kw_hit_rate"] for h in per_query_hit]),
                "avg_tag_hit_rate": _avg_optional([h["tag_hit_rate"] for h in per_query_hit]),
                "queries_with_new_kw": sum(1 for h in per_query_hit if h["new_kw_count"] > 0),
                "queries_with_new_tag": sum(1 for h in per_query_hit if h["new_tag_count"] > 0),
                "per_query": per_query_hit,
            }

    _save_json(METRICS_JSON_PATH, per_config)

    # 主指标对比表
    a_no = per_config["no_expansion"]["average"]
    a_yes = per_config["with_expansion"]["average"]
    delta_row = {
        f"P@{k}": a_yes.get(f"P@{k}", 0) - a_no.get(f"P@{k}", 0) for k in K_VALUES
    } | {
        f"nDCG@{k}": a_yes.get(f"nDCG@{k}", 0) - a_no.get(f"nDCG@{k}", 0) for k in K_VALUES
    }

    lines = [
        "## §7.4 Expansion 主指标对比",
        "",
        "| Config | P@5 | P@10 | nDCG@5 | nDCG@10 |",
        "|--------|-----|------|--------|---------|",
        f"| no_expansion   | {a_no.get('P@5',0):.3f} | {a_no.get('P@10',0):.3f} | {a_no.get('nDCG@5',0):.3f} | {a_no.get('nDCG@10',0):.3f} |",
        f"| with_expansion | {a_yes.get('P@5',0):.3f} | {a_yes.get('P@10',0):.3f} | {a_yes.get('nDCG@5',0):.3f} | {a_yes.get('nDCG@10',0):.3f} |",
        f"| **Δ**          | {delta_row['P@5']:+.3f} | {delta_row['P@10']:+.3f} | {delta_row['nDCG@5']:+.3f} | {delta_row['nDCG@10']:+.3f} |",
        "",
        "## §7.4 扩展命中率（仅 with_expansion）",
        "",
    ]
    hit = per_config["with_expansion"].get("hit_rate", {})
    if hit:
        kw_avg = hit.get("avg_kw_hit_rate")
        tag_avg = hit.get("avg_tag_hit_rate")
        lines += [
            f"- avg_kw_hit_rate  = {kw_avg:.3f}" if kw_avg is not None else "- avg_kw_hit_rate  = (无新增 keyword 的查询)",
            f"- avg_tag_hit_rate = {tag_avg:.3f}" if tag_avg is not None else "- avg_tag_hit_rate = (无新增 tag 的查询)",
            f"- 含新增 keyword 的查询数: {hit['queries_with_new_kw']}",
            f"- 含新增 tag 的查询数: {hit['queries_with_new_tag']}",
        ]

    table = "\n".join(lines)
    METRICS_MD_PATH.write_text(table + "\n", encoding="utf-8")
    print(table)
    print(f"\n[phase-c] metrics.json → {METRICS_JSON_PATH}")
    print(f"[phase-c] table.md    → {METRICS_MD_PATH}")
    return per_config


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["phase_a", "phase_b", "phase_c", "all"])
    parser.add_argument("--force-a", action="store_true")
    parser.add_argument("--force-b", action="store_true")
    args = parser.parse_args()

    queries = load_expansion_queries()

    if args.phase == "phase_a":
        run_phase_a(queries, force=args.force_a)
    elif args.phase == "phase_b":
        run_phase_b(queries, force=args.force_b)
    elif args.phase == "phase_c":
        run_phase_c()
    elif args.phase == "all":
        run_phase_a(queries, force=args.force_a)
        run_phase_b(queries, force=args.force_b)
        run_phase_c()


if __name__ == "__main__":
    main()
