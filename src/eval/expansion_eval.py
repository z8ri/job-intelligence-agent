"""
Section 7.4 standalone query-expansion evaluation: compare with/without
expansion on 18 abbreviation-sensitive queries.

Differences from pool_eval.py:
  - separate test set (test_queries_expansion.json, 18 queries vs 40)
  - only two configs: with_expansion / no_expansion (all other flags follow the
    Section 7.7 baseline)
  - fully separate cache paths (expansion_*.json) so the Section 7.7 headline
    numbers are never polluted
  - an extra expansion_hit_rate metric (how often expansion terms appear in the
    top-10 documents)

Reused from pool_eval: apply_config_to_prefs / score_one_job / build_pool /
_rate_one / _job_snippet / POOL_SYSTEM_PROMPT / _load_or_init / _save_json.

Usage:
    python -m src.eval.expansion_eval phase_a       # ranking (no LLM cost)
    python -m src.eval.expansion_eval phase_b       # pool annotation (gpt-4o-mini, ~$0.05)
    python -m src.eval.expansion_eval phase_c       # metrics + hit_rate + report
    python -m src.eval.expansion_eval all           # A -> B -> C
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
# Separate path constants; never import the same-named constants from pool_eval
# ---------------------------------------------------------------------------
RESULTS_DIR = PROJECT_ROOT / "data" / "eval_results"
QUERIES_PATH = PROJECT_ROOT / "data" / "test_queries_expansion.json"
PREF_CACHE_PATH = RESULTS_DIR / "expansion_preferences_cache.json"
RANKINGS_PATH = RESULTS_DIR / "expansion_rankings.json"
POOL_PATH = RESULTS_DIR / "expansion_pool_annotations.json"
METRICS_JSON_PATH = RESULTS_DIR / "expansion_metrics.json"
METRICS_MD_PATH = RESULTS_DIR / "expansion_metrics_table.md"

# Two configs: identical to the Section 7.7 baseline except for skip_expansion
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
# Test set loading
# ---------------------------------------------------------------------------

def load_expansion_queries() -> list[dict]:
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Preference cache (local path)
# ---------------------------------------------------------------------------

def cache_preferences(queries: list[dict], force: bool = False) -> dict:
    cache = {} if force else _load_or_init(PREF_CACHE_PATH, {})
    missing = [q for q in queries if q["id"] not in cache]
    if not missing:
        print(f"[pref-cache] {len(queries)}/{len(queries)} hits, skipping LLM calls")
        return cache

    print(f"[pref-cache] {len(missing)} LLM calls needed (gpt-4o-mini)")
    for q in missing:
        try:
            result = parse_preferences(q["query"])
            cache[q["id"]] = {
                "preferences": result["preferences"],
                "weights": result["weights"],
            }
            print(f"  [{q['id']}] ok")
        except Exception as e:
            print(f"  [{q['id']}] failed: {e}")
        _save_json(PREF_CACHE_PATH, cache)
    return cache


# ---------------------------------------------------------------------------
# Phase A: ranking under both configs
# ---------------------------------------------------------------------------

def run_phase_a(queries: list[dict], force: bool = False) -> dict:
    if RANKINGS_PATH.exists() and not force:
        print(f"[phase-a] {RANKINGS_PATH.name} already exists; use --force-a to overwrite")
        return _load_or_init(RANKINGS_PATH, {})

    pref_cache = cache_preferences(queries)

    print("[phase-a] Loading candidates + TF-IDF + ScoringEngine ...")
    all_candidates = load_candidates()
    print(f"  Candidates: {len(all_candidates)}")

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
            print(f"  [{qid}] no preferences, skipping")
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

        # Sanity check: the two configs' top-10 should not be identical
        a = rankings["no_expansion"].get(qid, [])
        b = rankings["with_expansion"].get(qid, [])
        same = "(IDENTICAL -- warning)" if a == b else f"(diff={len(set(a) ^ set(b))})"
        print(f"  [{qid}] done {same}")

    _save_json(RANKINGS_PATH, rankings)
    print(f"[phase-a] Written to {RANKINGS_PATH}")
    return rankings


# ---------------------------------------------------------------------------
# Phase B: pooled LLM annotation (local path)
# ---------------------------------------------------------------------------

def run_phase_b(queries: list[dict], force: bool = False) -> dict:
    rankings = _load_or_init(RANKINGS_PATH, None)
    if rankings is None:
        print("[phase-b] rankings missing; run phase_a first")
        sys.exit(1)

    pool = build_pool(rankings)
    total = sum(len(ids) for ids in pool.values())
    print(f"[phase-b] Pool size: {len(pool)} queries x avg {total / max(1,len(pool)):.1f} jobs = {total} to annotate")

    if total > 500:
        print(f"[phase-b] {total} annotations > 500 exceeds the budget guard; stopping. Trim the test set or check phase_a for anomalies")
        sys.exit(1)

    annotations = {} if force else _load_or_init(POOL_PATH, {})
    qtext = {q["id"]: q["query"] for q in queries}

    print("[phase-b] Loading candidates (to build job descriptions for annotation)...")
    all_candidates = load_candidates()
    job_by_id = {j["job_id"]: j for j in all_candidates}

    client = get_client()
    pending = sum(
        1
        for qid, ids in pool.items()
        for jid in ids
        if not (qid in annotations and jid in annotations[qid])
    )
    print(f"[phase-b] {pending} new annotations needed (gpt-4o-mini)")
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
                print(f"    [{qid}/{jid}] job not found in DB, recording 0")
                annotations[qid][jid] = 0
                continue
            grade = _rate_one(client, qtext[qid], job)
            if grade is None:
                print(f"    [{qid}/{jid}] annotation failed -> recording 0 (conservative)")
                grade = 0
            annotations[qid][jid] = grade
            done += 1
            if done % 20 == 0:
                print(f"    progress {done}/{pending}")
                _save_json(POOL_PATH, annotations)
        _save_json(POOL_PATH, annotations)

    _save_json(POOL_PATH, annotations)
    print(f"[phase-b] {done} new annotations done -> {POOL_PATH}")
    return annotations


# ---------------------------------------------------------------------------
# Expansion hit rate
# ---------------------------------------------------------------------------

def expansion_hit_rate(prefs: dict, top10_jobs: list[dict], expander: QueryExpander) -> dict:
    """
    Expansion hit rate: the fraction of keywords/tags newly added by expansion
    that appear in the top-10 documents (description + tags + title).

    Returns:
        {
          "kw_hit_rate":  float | None,   # fraction of new keywords that hit (None if no new keywords)
          "tag_hit_rate": float | None,
          "new_kw_count": int,
          "new_tag_count": int,
          "new_kw_hit_list": [str],       # expansion keywords that hit
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
# Phase C: metrics + hit_rate + table
# ---------------------------------------------------------------------------

def run_phase_c() -> dict:
    rankings = _load_or_init(RANKINGS_PATH, None)
    annotations = _load_or_init(POOL_PATH, None)
    if rankings is None or annotations is None:
        print("[phase-c] both rankings and pool_annotations must be ready")
        sys.exit(1)

    queries = load_expansion_queries()
    pref_cache = _load_or_init(PREF_CACHE_PATH, {})

    print("[phase-c] Loading candidates to compute hit_rate ...")
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

            # hit_rate only applies to with_expansion (no_expansion does no expansion)
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

    # Headline metric comparison table
    a_no = per_config["no_expansion"]["average"]
    a_yes = per_config["with_expansion"]["average"]
    delta_row = {
        f"P@{k}": a_yes.get(f"P@{k}", 0) - a_no.get(f"P@{k}", 0) for k in K_VALUES
    } | {
        f"nDCG@{k}": a_yes.get(f"nDCG@{k}", 0) - a_no.get(f"nDCG@{k}", 0) for k in K_VALUES
    }

    lines = [
        "## Section 7.4 Expansion headline metrics",
        "",
        "| Config | P@5 | P@10 | nDCG@5 | nDCG@10 |",
        "|--------|-----|------|--------|---------|",
        f"| no_expansion   | {a_no.get('P@5',0):.3f} | {a_no.get('P@10',0):.3f} | {a_no.get('nDCG@5',0):.3f} | {a_no.get('nDCG@10',0):.3f} |",
        f"| with_expansion | {a_yes.get('P@5',0):.3f} | {a_yes.get('P@10',0):.3f} | {a_yes.get('nDCG@5',0):.3f} | {a_yes.get('nDCG@10',0):.3f} |",
        f"| **Δ**          | {delta_row['P@5']:+.3f} | {delta_row['P@10']:+.3f} | {delta_row['nDCG@5']:+.3f} | {delta_row['nDCG@10']:+.3f} |",
        "",
        "## Section 7.4 Expansion hit rate (with_expansion only)",
        "",
    ]
    hit = per_config["with_expansion"].get("hit_rate", {})
    if hit:
        kw_avg = hit.get("avg_kw_hit_rate")
        tag_avg = hit.get("avg_tag_hit_rate")
        lines += [
            f"- avg_kw_hit_rate  = {kw_avg:.3f}" if kw_avg is not None else "- avg_kw_hit_rate  = (no query gained new keywords)",
            f"- avg_tag_hit_rate = {tag_avg:.3f}" if tag_avg is not None else "- avg_tag_hit_rate = (no query gained new tags)",
            f"- Queries with new keywords: {hit['queries_with_new_kw']}",
            f"- Queries with new tags: {hit['queries_with_new_tag']}",
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
