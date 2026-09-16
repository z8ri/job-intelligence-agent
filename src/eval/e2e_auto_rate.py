"""
Section 7.6 end-to-end answer quality: single-rater automatic scoring with
gpt-4o-mini (option B).

After the 2026-04-23 switch to two data sources, Section 7.6 had to be re-run on
the new data. The original approach (manually pasting prompts into 3 LLMs) costs
time, so this falls back to automatic scoring by gpt-4o-mini alone. The numbers
then line up with this report's dataset, at the cost of having no inter-rater
agreement (ICC / Cronbach's alpha).

Reads:   data/eval_results/e2e_queries.json   (produced by prepare_e2e_queries)
Writes:  data/reviews_e2e/gpt4omini.json      (one {query_id, relevance:{c,s}, ...} per query)
         data/eval_results/e2e_metrics.json   (single-rater macro mean + per-dimension distribution)
         data/eval_results/e2e_report.md

Usage:
    python -m src.eval.e2e_auto_rate

Cost:
    20 gpt-4o-mini calls, roughly $0.02
"""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from src.llm import MODEL, get_client

ROOT = Path(__file__).resolve().parent.parent.parent
# Output can be redirected via environment variables (e.g. when running the vNext
# pipeline for comparison, so historical results cited by the delivered report are
# not overwritten). Default behavior is unchanged.
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
    print(f"Loaded {len(records)} e2e_queries records")

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
            print(f"[{i}/{len(records)}] {qid} cached")
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
    print(f"Rating complete: {len(out)}/{len(records)} -> {REVIEW_OUT}")
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
        "# End-to-End Answer Quality Report (Section 7.6)",
        "",
        f"- Queries: **{metrics['total_queries']}** (selected from the 40 test_queries, covering 7 categories + multi-field combinations + hard filters)",
        f"- Data source: HN + Greenhouse, 2311 jobs (2026-04-23)",
        f"- Rater: **{metrics['rater']}**, single-rater automatic scoring (option B, cost $0.02)",
        "- Dimensions: Relevance (do the jobs match the query's core constraints) / Completeness (does the answer cover the fields in the query and justify each pick) / Readability (structure and readability)",
        "",
        "## Overall scores (single-rater macro mean)",
        "",
        "| Dimension | Macro mean (1-5) | Distribution |",
        "|---|---|---|",
    ]
    for d in DIMENSIONS:
        mm = metrics["macro_mean"].get(d, "N/A")
        dist = metrics["score_distribution"].get(d, {})
        dist_str = ", ".join(f"{k}:{v}" for k, v in dist.items())
        lines.append(f"| {d} | {mm} | {dist_str} |")

    lines.extend([
        "",
        "> This section uses single-rater (gpt-4o-mini) automatic scoring; ICC / Cronbach's alpha are not computed.",
        "",
        "## Per-query details",
        "",
        "| query_id | query | relevance | completeness | readability | mean |",
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
        print(f"[error] {E2E_PATH} not found; run prepare_e2e_queries first", file=sys.stderr)
        return 1
    if not os.environ.get("OPENAI_API_KEY"):
        print("[error] OPENAI_API_KEY is not set", file=sys.stderr)
        return 1

    ratings = run_rating()
    metrics = compute_metrics(ratings)
    write_report(ratings, metrics)

    print()
    print("Macro mean:")
    for d in DIMENSIONS:
        print(f"  {d:<14} {metrics['macro_mean'].get(d, 'N/A')}")
    print(f"Written:")
    print(f"  - {REVIEW_OUT}")
    print(f"  - {METRICS_PATH}")
    print(f"  - {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
