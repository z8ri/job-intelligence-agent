"""
Section 7.6 end-to-end answer quality: export the rating prompt for the three LLMs.

Reads data/eval_results/e2e_queries.json (20 queries + top-10 + system answer)
and generates a markdown file that can be pasted directly into claude.ai /
chatgpt.com / gemini.google.com.

Each LLM independently rates every (query, answer) pair on three dimensions:
- Relevance 1-5: do the returned jobs really match the query's core constraints
- Completeness 1-5: does the answer cover every important field the query touches
- Readability 1-5: clear language, easy-to-read structure, no redundancy
For each dimension the rater writes a short comment before the score (reduces
number-only hallucination).

Usage:
    python -m src.eval.export_e2e_review

Output:
    data/e2e_review_prompt.md
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
E2E_PATH = ROOT / "data" / "eval_results" / "e2e_queries.json"
PROMPT_OUT = ROOT / "data" / "e2e_review_prompt.md"

HEADER = """\
# Job Search End-to-End Answer Quality Evaluation

You are an independent evaluator for a job-search system. For each of the 20 queries below, you will see:
- the user's natural language query
- the structured preferences the system extracted
- the top-10 jobs the ranker chose
- the system's final natural language answer

Your job is to rate the **final answer** on three dimensions using a 1-5 integer scale. Be a strict but fair reviewer — do NOT be lenient. Use the full 1-5 range.

## Scoring dimensions

### 1. Relevance (相关性)
Do the jobs in the answer actually match the user's core constraints (salary, location, remote mode, tech stack, category)?
- **5** = Every highlighted job matches all hard constraints from the query.
- **4** = Most jobs match; one or two minor mismatches.
- **3** = Roughly half match; notable misses on salary/location/remote/stack.
- **2** = Most jobs violate one or more explicit constraints.
- **1** = Answer appears unrelated to the query.

### 2. Completeness (完整性)
Does the answer cover the aspects the user asked about? Does it explain WHY each job matches (citing salary fit, location, tech stack, remote mode, etc.)?
- **5** = Addresses every mentioned field; clearly justifies each pick against query constraints.
- **4** = Covers most fields; justifications are mostly present.
- **3** = Covers the main ask but skips one or two query dimensions.
- **2** = Superficial — listing jobs without tying back to query constraints.
- **1** = Does not engage with the query's dimensions at all.

### 3. Readability (可读性)
Is the answer well-structured, concise, and easy to scan?
- **5** = Clean numbered list, consistent structure, no filler, easy to scan.
- **4** = Well-structured with minor wordiness or inconsistency.
- **3** = Understandable but wall-of-text or uneven formatting.
- **2** = Rambling, repetitive, or poorly organized.
- **1** = Confusing or incoherent.

For each dimension, first write one short comment (≤30 words) explaining your rating, then give the integer 1-5.

## Output format

Output **ONLY** a single JSON array in the exact order of the queries below. No explanation, no extra text, no markdown fences.

```json
[
  {
    "query_id": "q01",
    "relevance": {"comment": "All top-3 are remote Python backend above 150k; strong match.", "score": 5},
    "completeness": {"comment": "Explains salary/remote/stack per job, but omits explicit category label.", "score": 4},
    "readability": {"comment": "Clean numbered list; slightly verbose summary paragraph.", "score": 4}
  },
  {"query_id": "q05", "relevance": {...}, "completeness": {...}, "readability": {...}}
]
```

---

"""


def _format_job_block(job: dict, rank: int) -> list[str]:
    lines = [f"- **#{rank}** {job.get('title', 'N/A')} @ {job.get('company', 'N/A')}"]
    loc = job.get("location") or "N/A"
    remote = job.get("remote") or "unknown"
    lines.append(f"  - Location: {loc} | Remote: {remote}")

    s_min = job.get("salary_min")
    s_max = job.get("salary_max")
    if s_min and s_max:
        lines.append(f"  - Salary: ${s_min:,} – ${s_max:,}")
    elif s_min:
        lines.append(f"  - Salary: ${s_min:,}+")
    elif s_max:
        lines.append(f"  - Salary: up to ${s_max:,}")
    else:
        lines.append("  - Salary: not specified")

    tags = job.get("tags") or []
    if tags:
        lines.append(f"  - Tags: {', '.join(tags[:10])}")

    cat = job.get("predicted_category") or job.get("category") or "other"
    lines.append(f"  - Category: {cat}")

    fs = job.get("final_score")
    if fs is not None:
        lines.append(f"  - Final score: {fs:.3f}")

    desc = (job.get("description") or "").strip().replace("\n", " ")
    if desc:
        snippet = desc[:240] + ("…" if len(desc) > 240 else "")
        lines.append(f"  - Snippet: {snippet}")
    return lines


def main() -> int:
    if not E2E_PATH.exists():
        print(f"[error] {E2E_PATH} not found; run prepare_e2e_queries first", file=sys.stderr)
        return 1

    with E2E_PATH.open("r", encoding="utf-8") as f:
        records = json.load(f)

    parts = [HEADER, f"## 20 queries to rate\n"]
    for rec in records:
        qid = rec["query_id"]
        parts.append(f"### {qid}")
        parts.append(f"**User query:** {rec['query']}\n")
        prefs = rec.get("preferences") or {}
        parts.append("**Extracted preferences:**")
        parts.append("```json")
        parts.append(json.dumps(prefs, ensure_ascii=False, indent=2))
        parts.append("```\n")

        top = rec.get("top_jobs") or []
        if top:
            parts.append(f"**Top-{len(top)} retrieved jobs:**")
            for i, job in enumerate(top, start=1):
                parts.extend(_format_job_block(job, i))
            parts.append("")
        else:
            parts.append("**Top retrieved jobs:** (empty)\n")

        answer = rec.get("answer") or "(empty)"
        parts.append("**System answer to rate:**")
        parts.append("")
        parts.append(answer)
        parts.append("\n---\n")

    PROMPT_OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Exported {len(records)} queries to {PROMPT_OUT}")
    print()
    print("Next: paste the whole file into:")
    print("  - claude.ai          -> save the reply to data/reviews_e2e/claude.json")
    print("  - chatgpt.com        -> save the reply to data/reviews_e2e/chatgpt.json")
    print("  - gemini.google.com  -> save the reply to data/reviews_e2e/gemini.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
