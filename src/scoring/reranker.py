"""LLM reranking: a finer-grained query-job relevance judgment over the first-stage Top-N.

BM25/TF-IDF look at lexical overlap and Dense at overall semantic similarity;
neither jointly considers "what exactly is this query asking, and does this job
actually satisfy it". Here GPT-4o-mini scores each Top-N candidate's title +
summary against the query (LLM + schema style with structured output; the LLM
does not decide the recommendations directly), replacing the coarser part of the
first-stage scores.
"""

import json

from src.llm import MODEL, get_client
from src.observability import log_call, timed_call

RERANK_TOP_N = 50
# Many job descriptions open with company boilerplate ("XX is growing our team
# of..."), and the real responsibilities/skills often only appear several hundred
# characters in. A 300-char cutoff was observed to truncate the summary inside
# that boilerplate, leaving the LLM no substantive information and distorting
# relevance scores. 1200 chars covers the substance of most postings while the
# API cost stays negligible (50 candidates is roughly 15k tokens, a fraction of a
# cent per call).
_MAX_DESC_CHARS = 1200

SYSTEM_PROMPT = """You are a job search relevance judge. Given a user query and \
a list of job postings (id, title, short description), score how well each \
job matches the query's intent on a 0.0-1.0 scale (1.0 = perfectly relevant, \
0.0 = unrelated). Judge relevance only — ignore salary/location/remote, those \
are scored separately downstream.
Output ONLY a JSON object mapping job id -> score, e.g. {"hn_123": 0.85, ...}.
No explanation, no markdown."""


def rerank(
    query: str,
    candidates: list[dict],
    top_n: int = RERANK_TOP_N,
    api_key: str | None = None,
    run_id: str | None = None,
) -> dict[str, float]:
    """LLM-rerank the first top_n candidates and return {job_id: score}.

    candidates must already be sorted by first-stage score descending (the caller
    is responsible for that). On any failure (network, JSON parsing, malformed
    output) degrade gracefully by returning {}: the caller then skips the
    overwrite and the original first-stage ranking is kept as is. No retries, and
    the pipeline is never interrupted (reranking is a nice-to-have, not critical path).
    """
    subset = candidates[:top_n]
    if not subset:
        return {}

    listing = [
        {
            "id": c["job_id"],
            "title": c.get("title") or "",
            "summary": (c.get("description") or "")[:_MAX_DESC_CHARS],
        }
        for c in subset
    ]
    valid_ids = {c["job_id"] for c in subset}

    t = None
    try:
        client = get_client(api_key)
        with timed_call() as t:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Query: {query}\n\nJobs:\n{json.dumps(listing)}"},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
        usage = resp.usage
        data = json.loads(resp.choices[0].message.content)
    except Exception as e:
        log_call(run_id, "reranker", MODEL, getattr(t, "elapsed_ms", 0.0), success=False, error=str(e))
        return {}
    log_call(
        run_id, "reranker", MODEL, t.elapsed_ms,
        prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
    )

    if not isinstance(data, dict):
        return {}

    scores: dict[str, float] = {}
    for jid, val in data.items():
        if jid not in valid_ids:
            continue  # ignore ids the LLM made up that are not among the candidates
        try:
            scores[jid] = max(0.0, min(1.0, float(val)))
        except (TypeError, ValueError):
            continue
    return scores
