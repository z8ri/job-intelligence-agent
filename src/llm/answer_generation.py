"""
LLM answer generation (post-processing stage).

Feeds the top-K results ranked by the scoring engine, together with the user's
original question, to the LLM to produce a structured natural-language answer.
The LLM does not affect the ranking.

Grounding design: company/title/location/salary/tags are rendered directly
from the retrieved job record, never from LLM output — the LLM is only asked
for the subjective "why it matches / tradeoffs" narrative per job (structured
JSON, one entry per job_id actually given to it), which is then interleaved
with the deterministic facts. This makes it structurally impossible for the
LLM to introduce a job that wasn't retrieved, and a best-effort fact-check
(`_salary_fact_check`) flags a narrative that states a salary figure
inconsistent with the job's real salary range.
"""

import json
import re

from src.llm import MODEL, get_client
from src.observability import log_call, timed_call

NARRATIVE_SYSTEM_PROMPT = """\
You are a job search assistant. The user asked a question about jobs, and a retrieval system has already found, ranked, and fact-checked the best matching positions — you are only responsible for explaining the match, not restating or inventing facts.

For each job (identified by its job_id), you are given its real facts (company, title, location, salary, tags, score breakdown). Write a short narrative (1-3 sentences) explaining WHY it matches the user's query and any tradeoffs — reference the given facts, but do not state a salary figure, location, or other detail that isn't already in the facts given to you.

Also write a brief closing summary (1-2 sentences) comparing the top picks.

If a job has a "Verification note", honestly mention that caveat — don't treat it as fully confirmed.

Respond in the same language as the user's query.

Output ONLY a JSON object, no markdown fences:
{"per_job": {"<job_id>": "<narrative for this job>", ...}, "summary": "<closing summary>"}
Every job_id given to you must have an entry in "per_job"."""


def _format_job_for_prompt(job: dict, rank: int | None) -> str:
    """Format a single job and its scores as an entry in the prompt. rank=None
    omits the "### Result #N" heading (used when the caller already printed
    its own heading, e.g. a job_id header for the narrative prompt)."""
    lines = [f"### Result #{rank}"] if rank is not None else []
    lines.append(f"- Company: {job.get('company', 'N/A')}")
    lines.append(f"- Title: {job.get('title', 'N/A')}")
    lines.append(f"- Location: {job.get('location', 'N/A')}")
    lines.append(f"- Remote: {job.get('remote', 'unknown')}")

    sal_min = job.get("salary_min")
    sal_max = job.get("salary_max")
    if sal_min and sal_max:
        lines.append(f"- Salary: ${sal_min:,} - ${sal_max:,}")
    elif sal_min:
        lines.append(f"- Salary: ${sal_min:,}+")
    elif sal_max:
        lines.append(f"- Salary: up to ${sal_max:,}")
    else:
        lines.append("- Salary: not specified")

    tags = job.get("tags", [])
    if tags:
        lines.append(f"- Tags: {', '.join(tags)}")

    category = job.get("category", "other")
    lines.append(f"- Category: {category}")

    scores = job.get("score_breakdown", {})
    if scores:
        score_parts = [f"{k}={v:.2f}" for k, v in scores.items()]
        lines.append(f"- Score breakdown: {', '.join(score_parts)}")

    final_score = job.get("final_score")
    if final_score is not None:
        lines.append(f"- **Final score: {final_score:.3f}**")

    if job.get("verification_status") == "unknown":
        lines.append(f"- ⚠ Verification note: {job.get('verification_reason', '')}")

    desc = job.get("description", "")
    if desc:
        snippet = desc[:200] + "..." if len(desc) > 200 else desc
        lines.append(f"- Description snippet: {snippet}")

    return "\n".join(lines)


def _build_narrative_messages(user_query: str, ranked_jobs: list[dict], preferences: dict | None = None) -> list[dict]:
    """Build the message list asking the LLM for a per-job_id narrative only —
    the facts it's given are the same ones rendered to the user, so it has
    what it needs to explain the match without inventing anything."""
    messages = [{"role": "system", "content": NARRATIVE_SYSTEM_PROMPT}]

    user_content = f"## User Query\n{user_query}\n\n"

    if preferences:
        user_content += "## Extracted Preferences\n```json\n"
        user_content += json.dumps(preferences, indent=2)
        user_content += "\n```\n\n"

    user_content += f"## Ranked Results ({len(ranked_jobs)} jobs, job_id in each heading)\n\n"

    for job in ranked_jobs:
        user_content += f"### job_id: {job.get('job_id')}\n"
        user_content += _format_job_for_prompt(job, rank=None) + "\n\n"

    messages.append({"role": "user", "content": user_content})
    return messages


_DOLLAR_AMOUNT_RE = re.compile(r"\$\s*([\d][\d,]*(?:\.\d+)?)\s*([kK])?")
_BARE_K_AMOUNT_RE = re.compile(r"(?<![\d.\$])(\d+(?:\.\d+)?)\s*[kK]\b")


def _extract_salary_mentions(text: str) -> list[int]:
    """Best-effort extraction of dollar figures from free text (handles "$150k",
    "$150,000", "150k"). This is a heuristic regex, not real NLP — it won't
    catch every phrasing (e.g. spelled-out numbers), so treat a clean result as
    reassuring, not as proof there's no mismatch."""
    mentions = []
    for m in _DOLLAR_AMOUNT_RE.finditer(text):
        num = float(m.group(1).replace(",", ""))
        if m.group(2):
            num *= 1000
        mentions.append(int(num))
    for m in _BARE_K_AMOUNT_RE.finditer(text):
        mentions.append(int(float(m.group(1)) * 1000))
    return [n for n in mentions if 10_000 <= n <= 2_000_000]


def _salary_fact_check(narrative: str, job: dict) -> str | None:
    """Flags a narrative that states a salary figure outside the job's real
    range. Salary-only: location and other fields aren't checked here (harder
    to match reliably against free text without false positives)."""
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    if not salary_min and not salary_max:
        return None
    lo = salary_min or salary_max
    hi = salary_max or salary_min
    tolerance = 0.05  # allow "about $150k" to match a real $148,000
    lo_bound, hi_bound = lo * (1 - tolerance), hi * (1 + tolerance)
    for amount in _extract_salary_mentions(narrative):
        if not (lo_bound <= amount <= hi_bound):
            return f"narrative mentions ${amount:,}, outside this posting's stated ${lo:,}-${hi:,}"
    return None


def _render_job_block(job: dict, rank: int, narrative: str) -> str:
    """Deterministic rendering of one result: facts come straight from the job
    record, never from the LLM. Only `narrative` is LLM-written."""
    lines = [f"{rank}. **{job.get('title', 'N/A')}** @ {job.get('company', 'N/A')}"]

    sal_min, sal_max = job.get("salary_min"), job.get("salary_max")
    if sal_min and sal_max:
        salary = f"${sal_min:,}-${sal_max:,}"
    elif sal_min:
        salary = f"${sal_min:,}+"
    elif sal_max:
        salary = f"up to ${sal_max:,}"
    else:
        salary = "not specified"

    lines.append(
        f"   - Location: {job.get('location', 'N/A')} | Remote: {job.get('remote', 'unknown')} | Salary: {salary}"
    )
    tags = job.get("tags", [])
    if tags:
        lines.append(f"   - Tags: {', '.join(tags)}")
    if job.get("verification_status") == "unknown":
        lines.append(f"   - ⚠ Verification note: {job.get('verification_reason', '')}")

    fact_check_warning = _salary_fact_check(narrative, job)
    if fact_check_warning:
        lines.append(f"   - ⚠ Fact-check note: {fact_check_warning}")

    lines.append(f"   - {narrative}")
    return "\n".join(lines)


def generate_answer(
    user_query: str,
    ranked_jobs: list[dict],
    preferences: dict | None = None,
    api_key: str | None = None,
    run_id: str | None = None,
) -> str:
    """
    Main entry point: generate a natural-language answer from retrieval results.

    Grounding: the LLM only supplies a per-job narrative (JSON, keyed by
    job_id); company/title/location/salary/tags are rendered directly from
    `ranked_jobs`, not from the LLM's output, so it cannot introduce a job that
    wasn't retrieved or restate a fact incorrectly for a job that was. A
    best-effort fact-check flags a narrative that states a salary figure
    outside the job's real range (see `_salary_fact_check`).

    Args:
        user_query: the user's original query
        ranked_jobs: top-K jobs ranked by the scoring engine; each dict should contain:
            - all columns of the jobs table (including job_id)
            - tags: list[str]
            - final_score: float
            - score_breakdown: dict (per-dimension scores)
        preferences: preference dict extracted by query understanding (optional;
            helps the LLM explain the matching logic)
        api_key: OpenAI API key
        run_id: pipeline run identifier, threaded through to the observability trace

    Returns:
        The natural-language answer string
    """
    if not ranked_jobs:
        return "No matching jobs found. Try broadening your search criteria."

    client = get_client(api_key)
    messages = _build_narrative_messages(user_query, ranked_jobs, preferences)

    try:
        with timed_call() as t:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
        usage = response.usage
        data = json.loads(response.choices[0].message.content)
    except Exception as e:
        log_call(run_id, "answer_generation", MODEL, getattr(t, "elapsed_ms", 0.0), success=False, error=str(e))
        raise

    log_call(
        run_id, "answer_generation", MODEL, t.elapsed_ms,
        prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
    )

    per_job = data.get("per_job", {}) if isinstance(data, dict) else {}
    summary = data.get("summary", "") if isinstance(data, dict) else ""

    blocks = []
    for i, job in enumerate(ranked_jobs, 1):
        # `.get(key) or default` (not `.get(key, default)`) — a present-but-empty
        # value (null, "") must also fall back, not just a missing key.
        narrative = per_job.get(job.get("job_id")) or "(no narrative returned for this job)"
        if not isinstance(narrative, str):
            narrative = str(narrative)
        blocks.append(_render_job_block(job, i, narrative))

    answer = "\n\n".join(blocks)
    if summary:
        answer += f"\n\n**Summary:** {summary}"
    return answer


def format_fallback_answer(ranked_jobs: list[dict]) -> str:
    """Template-based answer with no LLM call, used when generate_answer fails
    after retries. Retrieval/ranking/verification already happened by this
    point, so degrade to a structured listing instead of dropping the results
    entirely — reuses the same per-job detail as the LLM prompt, just without
    narrative prose or query-specific explanations.
    """
    if not ranked_jobs:
        return "No matching jobs found. Try broadening your search criteria."

    lines = [
        "(Automated fallback: the answer-writing service is temporarily unavailable, "
        "showing the ranked results directly.)",
        "",
    ]
    for i, job in enumerate(ranked_jobs, 1):
        lines.append(_format_job_for_prompt(job, i))
        lines.append("")
    return "\n".join(lines)
