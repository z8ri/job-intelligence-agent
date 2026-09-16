"""
§7.6 端到端回答质量 — gpt-4o-mini 单评分员自动评分（选项 B）

2026-04-23 双源切换后，§7.6 需要在新数据下重跑。原方案 3 家 LLM 人工贴 prompt
成本是时间；这里退一步用 gpt-4o-mini 一家自动打分，数字对齐本报告数据集，
代价是没有跨评分员一致性 (ICC / Cronbach α)。

读取:  data/eval_results/e2e_queries.json   (prepare_e2e_queries 产出)
产出:  data/reviews_e2e/gpt4omini.json      (每条 {query_id, relevance:{c,s}, ...})
       data/eval_results/e2e_metrics.json   (单评分员 macro mean + 维度分布)
       data/eval_results/e2e_report.md

用法:
    python -m src.eval.e2e_auto_rate

成本:
    20 次 gpt-4o-mini 调用 ≈ $0.02
"""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from src.llm import MODEL, get_client

ROOT = Path(__file__).resolve().parent.parent.parent
# 允许通过环境变量重定向输出（例如跑 vNext 新 pipeline 对比时不覆盖已交付
# 报告引用的历史结果），默认行为不变。
E2E_RESULTS_DIR = Path(os.environ.get("E2E_EVAL_RESULTS_DIR") or (ROOT / "data" / "eval_results"))
E2E_REVIEWS_DIR = Path(os.environ.get("E2E_REVIEWS_DIR") or (ROOT / "data" / "reviews_e2e"))
E2E_PATH = E2E_RESULTS_DIR / "e2e_queries.json"
REVIEW_OUT = E2E_REVIEWS_DIR / "gpt4omini.json"
METRICS_PATH = E2E_RESULTS_DIR / "e2e_metrics.json"
REPORT_PATH = E2E_RESULTS_DIR / "e2e_report.md"

DIMENSIONS = ["relevance", "completeness", "readability"]

RATING_SYSTEM = """\
You are an independent evaluator for a job-search system. You will see a user's query, \
the structured preferences the system extracted, the top-10 jobs the ranker chose, and \
the system's final natural language answer.

Rate ONLY the final answer on three dimensions using a 1-5 integer scale. Be a strict but \
fair reviewer — do NOT be lenient. Use the full 1-5 range.

Scoring dimensions:
1. Relevance — Do the jobs in the answer actually match the user's core constraints \
(salary, location, remote mode, tech stack, category)?
   5 = every highlighted job matches all hard constraints; 4 = most match, one or two minor \
mismatches; 3 = roughly half match; 2 = most jobs violate one or more explicit constraints; \
1 = unrelated.
2. Completeness — Does the answer cover the aspects the user asked about? Does it explain \
WHY each job matches (citing salary fit, location, tech stack, remote mode, etc.)?
   5 = addresses every mentioned field with justification; 4 = covers most; 3 = main ask but \
skips one or two dimensions; 2 = superficial listing; 1 = no engagement.
3. Readability — Is the answer well-structured, concise, and easy to scan?
   5 = clean numbered list, consistent structure; 4 = minor wordiness; 3 = wall-of-text or \
uneven; 2 = rambling; 1 = confusing.

For each dimension, write one short comment (<=30 words) and an integer score 1-5.
Output ONLY a single JSON object in this exact shape:
{"relevance": {"comment": "...", "score": N}, \
"completeness": {"comment": "...", "score": N}, \
"readability": {"comment": "...", "score": N}}
No markdown fences, no extra text.
"""


def _format_job_block(job: dict, rank: int) -> list[str]:
    lines = [f"- #{rank} {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}"]
    loc = job.get("location") or "N/A"
    remote = job.get("remote") or "unknown"
    lines.append(f"  Location: {loc} | Remote: {remote}")

    s_min = job.get("salary_min")
    s_max = job.get("salary_max")
    if s_min and s_max:
        lines.append(f"  Salary: ${s_min:,} - ${s_max:,}")
    elif s_min:
        lines.append(f"  Salary: ${s_min:,}+")
    elif s_max:
        lines.append(f"  Salary: up to ${s_max:,}")
    else:
        lines.append("  Salary: n/a")

    tags = job.get("tags") or []
    if tags:
        lines.append(f"  Tags: {', '.join(tags[:10])}")

    cat = job.get("predicted_category") or job.get("category") or "other"
    lines.append(f"  Category: {cat}")

    desc = (job.get("description") or "").strip().replace("\n", " ")
    if desc:
        snippet = desc[:240] + ("..." if len(desc) > 240 else "")
        lines.append(f"  Snippet: {snippet}")
    return lines


def _build_user_prompt(rec: dict) -> str:
    parts = [f"User query: {rec['query']}", ""]
    prefs = rec.get("preferences") or {}
    parts.append("Extracted preferences (JSON):")
    parts.append(json.dumps(prefs, ensure_ascii=False))
    parts.append("")
    top = rec.get("top_jobs") or []
    if top:
        parts.append(f"Top-{len(top)} retrieved jobs:")
        for i, job in enumerate(top, start=1):
            parts.extend(_format_job_block(job, i))
        parts.append("")
    parts.append("System answer to rate:")
    parts.append(rec.get("answer") or "(empty)")
    return "\n".join(parts)


def _parse_rating(raw: str) -> dict | None:
    """Parse LLM output into {dim: {comment, score}}. None on failure."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    out = {}
    for d in DIMENSIONS:
        v = obj.get(d)
        if not isinstance(v, dict):
            return None
        try:
            s = int(v.get("score"))
        except (TypeError, ValueError):
            return None
        if not 1 <= s <= 5:
            return None
        out[d] = {"comment": str(v.get("comment", "")).strip(), "score": s}
    return out


def _rate_one(client, rec: dict) -> dict | None:
    messages = [
        {"role": "system", "content": RATING_SYSTEM},
        {"role": "user", "content": _build_user_prompt(rec)},
    ]
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=400,
            )
            raw = resp.choices[0].message.content or ""
            parsed = _parse_rating(raw)
            if parsed:
                return parsed
            print(f"    parse-fail attempt {attempt+1}: {raw[:120]!r}")
        except Exception as e:
            print(f"    LLM error attempt {attempt+1}: {e}")
            time.sleep(1.5)
    return None


def run_rating() -> list[dict]:
    with E2E_PATH.open("r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"加载 {len(records)} 条 e2e_queries")

    existing: dict[str, dict] = {}
    if REVIEW_OUT.exists():
        with REVIEW_OUT.open("r", encoding="utf-8") as f:
            for e in json.load(f):
                existing[e["query_id"]] = e

    client = get_client()
    out = []
    for i, rec in enumerate(records, start=1):
        qid = rec["query_id"]
        if qid in existing and all(d in existing[qid] for d in DIMENSIONS):
            out.append(existing[qid])
            print(f"[{i}/{len(records)}] {qid} 已缓存")
            continue
        rating = _rate_one(client, rec)
        if rating is None:
            print(f"[{i}/{len(records)}] {qid} FAIL")
            continue
        entry = {"query_id": qid, **rating}
        out.append(entry)
        print(f"[{i}/{len(records)}] {qid} "
              f"R={rating['relevance']['score']} "
              f"C={rating['completeness']['score']} "
              f"D={rating['readability']['score']}")
        REVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
        REVIEW_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    REVIEW_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"打分完成 {len(out)}/{len(records)} → {REVIEW_OUT}")
    return out


def compute_metrics(ratings: list[dict]) -> dict:
    dim_scores: dict[str, list[int]] = {d: [] for d in DIMENSIONS}
    dim_counter: dict[str, Counter] = {d: Counter() for d in DIMENSIONS}
    for r in ratings:
        for d in DIMENSIONS:
            s = r.get(d, {}).get("score")
            if s is not None:
                dim_scores[d].append(s)
                dim_counter[d][s] += 1

    macro_mean = {d: round(sum(dim_scores[d]) / len(dim_scores[d]), 3)
                  for d in DIMENSIONS if dim_scores[d]}
    distribution = {d: dict(sorted(dim_counter[d].items())) for d in DIMENSIONS}

    metrics = {
        "total_queries": len(ratings),
        "rater": "gpt-4o-mini (single)",
        "dimensions": DIMENSIONS,
        "macro_mean": macro_mean,
        "score_distribution": distribution,
        "note": "Single-rater auto evaluation (option B). ICC/Cronbach not applicable.",
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics


def write_report(ratings: list[dict], metrics: dict) -> None:
    with E2E_PATH.open("r", encoding="utf-8") as f:
        records = json.load(f)
    query_by_id = {r["query_id"]: r["query"] for r in records}

    lines = [
        "# 端到端回答质量评估报告 (§7.6)",
        "",
        f"- 查询数：**{metrics['total_queries']}** 条（从 40 条 test_queries 中挑选，覆盖 7 类别 + 多字段组合 + 硬过滤）",
        f"- 数据源：HN + Greenhouse 双源 2311 条 (2026-04-23)",
        f"- 打分者：**{metrics['rater']}** 单评分员自动评分（选项 B，成本 $0.02）",
        "- 三维定义：Relevance（职位是否匹配查询核心约束）/ Completeness（答案是否覆盖查询涉及字段且解释每个 pick）/ Readability（结构与可读性）",
        "",
        "## 三维总评（单评分员 macro mean）",
        "",
        "| 维度 | Macro mean (1-5) | 分布 |",
        "|---|---|---|",
    ]
    for d in DIMENSIONS:
        mm = metrics["macro_mean"].get(d, "N/A")
        dist = metrics["score_distribution"].get(d, {})
        dist_str = ", ".join(f"{k}:{v}" for k, v in dist.items())
        lines.append(f"| {d} | {mm} | {dist_str} |")

    lines.extend([
        "",
        "> 本节采用单评分员（gpt-4o-mini）自动评分，不计算 ICC / Cronbach α。",
        "",
        "## 每条 query 明细",
        "",
        "| query_id | query | relevance | completeness | readability | 平均 |",
        "|---|---|---|---|---|---|",
    ])
    for r in ratings:
        qid = r["query_id"]
        q = query_by_id.get(qid, "")
        q = (q[:40] + "...") if len(q) > 40 else q
        rs = r["relevance"]["score"]
        cs = r["completeness"]["score"]
        ds = r["readability"]["score"]
        avg = round((rs + cs + ds) / 3, 2)
        lines.append(f"| {qid} | {q} | {rs} | {cs} | {ds} | {avg} |")

    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not E2E_PATH.exists():
        print(f"[error] {E2E_PATH} not found，先跑 prepare_e2e_queries", file=sys.stderr)
        return 1
    if not os.environ.get("OPENAI_API_KEY"):
        print("[error] OPENAI_API_KEY 未设置", file=sys.stderr)
        return 1

    ratings = run_rating()
    metrics = compute_metrics(ratings)
    write_report(ratings, metrics)

    print()
    print("Macro mean:")
    for d in DIMENSIONS:
        print(f"  {d:<14} {metrics['macro_mean'].get(d, 'N/A')}")
    print(f"已写入:")
    print(f"  - {REVIEW_OUT}")
    print(f"  - {METRICS_PATH}")
    print(f"  - {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
