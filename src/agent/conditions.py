"""Turn a natural-language request into a ConditionSet via an LLM.

The LLM only extracts; the program validates. Every condition must quote the
user's words verbatim, so a hallucinated or paraphrased condition is caught here
rather than silently steering retrieval.
"""

from __future__ import annotations

import json
from typing import Callable

from pydantic import ValidationError

from src.agent.models import _norm, Clarification, Condition, ConditionSet
from src.llm import MODEL, get_client
from src.observability import log_call, timed_call

CompleteFn = Callable[[str, str], str]


class ConditionParseError(RuntimeError):
    pass


SYSTEM_PROMPT = """\
You extract structured job-search conditions from a user's request.

Return ONE JSON object: {"conditions": [...], "clarifications": [...]}.

Each condition:
{"field": <field>, "strength": "hard"|"soft", "value": {...}, "quote": "<exact words copied from the request>", "weight": number|null}

fields and their value shapes (value.kind must match):
- role_focus / role_avoid / skill / other -> {"kind":"text","text":"<English phrase>"}
- seniority -> {"kind":"experience","level":"intern|entry|junior|mid|senior|staff"|null,"max_years_required":int|null}
- employment_type -> {"kind":"employment","types":["full_time"|"part_time"|"internship"|"contract"]}
- work_region -> {"kind":"regions","regions":["New York", ...]}   where the user can work
- remote_mode -> {"kind":"modes","modes":["remote"|"hybrid"|"onsite"]}   which arrangements are acceptable
- salary -> {"kind":"salary","currency":"USD","period":"year","basis":"base|total|unspecified","min_amount":number|null,"region":string|null}

Rules:
- "quote" MUST be copied character-for-character from the request (same language). Never translate or paraphrase it.
- strength is "hard" only for a stated must / deal-breaker; wishes, "prefer", "can accept" are "soft".
- weight (0.1-1.0) only for soft conditions, reflecting how strongly the user stressed them ("最好", "particularly" -> 0.8-1.0; "if possible", "少量" -> 0.2-0.4); null when no emphasis was expressed. Hard conditions use null.
- work_region (where the user can work) and remote_mode (how the job is worked) are different conditions.
- Do not invent conditions the user did not state. Do not fill salary.min_amount unless a number was given.
- "avoid" wishes about the KIND OF WORK ("do not want mainly X") are role_avoid. "Accepts a little X" is a soft role_focus.
- Constraints about the employer, team or working conditions are `other`, never role_avoid: employer type ("no agencies", "not an outsourcing company", "a startup", "developer-tools company"), culture or on-call/crunch expectations, working hours or time zone ("evenings", "Pacific time zone", "Europe-friendly hours"), timing ("summer"), and "the posting states a salary range". "Only/must/no ..." makes them hard; "prefer/ideally" makes them soft.
- Statements that place no requirement produce NO condition: "X is not needed / not a problem / not important / doesn't matter", "whatever X", "travel is fine", "clearance is fine". An acceptance statement ("hybrid is fine", "contract is fine", "entry level is OK") is at most one soft condition holding ONLY the accepted value; never add the other values yourself.
- "X or Y" inside one field is ONE condition (regions: ["New York","Boston"]; modes: ["remote","hybrid"]; role_focus text "AI product or data science"; skill text "Go or Python"). Separate skills joined by "and"/commas are separate skill conditions. Put every named technology in its own skill condition, not inside role_focus.
- A level word next to a role ("Senior backend engineer") gives BOTH the role_focus and a seniority condition.
- salary: keep the period the user used (per hour -> "hour", per month -> "month", per year -> "year"); basis is "unspecified" unless the user says base or total/OTC; never invent one. Only create a salary condition when a number is given; a vague "pays well" gives no number, so make no salary condition and ask.
- work_region is where the user can/wants to work. A statement of where the user currently lives ("I am in New York") is not a region requirement. "I can work in the UK or EU" is a hard region condition.
- When one alternative crosses two fields ("Denver or remote", "Bay Area or remote"), do NOT emit an independent hard condition for each side; emit the other conditions and ask a clarification instead (affects the region/mode fields). Do the same when a number the request depends on is unclear ("at least 8 years of experience": the user's own or required by the job?; "not too far from X": how far?) and when the request is too vague to name a role.
- Add a clarification ONLY if the ambiguity would change which jobs qualify. Otherwise return [].
  clarification: {"question": str, "reason": str, "options": [str], "affects": [<field>]}
Output JSON only."""

EXAMPLE_USER = (
    "想找纽约可以工作的初级 LLM 应用开发全职岗位，可以混合办公，接受少量微调，但不希望主要做模型训练。"
)
EXAMPLE_ASSISTANT = json.dumps(
    {
        "conditions": [
            {"field": "role_focus", "strength": "hard", "quote": "LLM 应用开发",
             "value": {"kind": "text", "text": "LLM application development"}},
            {"field": "seniority", "strength": "hard", "quote": "初级",
             "value": {"kind": "experience", "level": "junior", "max_years_required": None}},
            {"field": "employment_type", "strength": "hard", "quote": "全职",
             "value": {"kind": "employment", "types": ["full_time"]}},
            {"field": "work_region", "strength": "hard", "quote": "纽约可以工作",
             "value": {"kind": "regions", "regions": ["New York"]}},
            {"field": "remote_mode", "strength": "soft", "quote": "可以混合办公",
             "value": {"kind": "modes", "modes": ["hybrid"]}},
            {"field": "role_focus", "strength": "soft", "quote": "接受少量微调",
             "value": {"kind": "text", "text": "some model fine-tuning"}, "weight": 0.3},
            {"field": "role_avoid", "strength": "soft", "quote": "不希望主要做模型训练",
             "value": {"kind": "text", "text": "primarily model training"}, "weight": 0.8},
        ],
        "clarifications": [],
    },
    ensure_ascii=False,
)


def _openai_complete(system: str, user: str, *, run_id: str | None = None) -> str:
    client = get_client()
    t = None
    try:
        with timed_call() as t:
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": EXAMPLE_USER},
                    {"role": "assistant", "content": EXAMPLE_ASSISTANT},
                    {"role": "user", "content": user},
                ],
            )
    except Exception as e:
        log_call(run_id, "conditions", MODEL, getattr(t, "elapsed_ms", 0.0), success=False, error=str(e))
        raise
    log_call(
        run_id, "conditions", MODEL, t.elapsed_ms,
        prompt_tokens=resp.usage.prompt_tokens, completion_tokens=resp.usage.completion_tokens,
    )
    return resp.choices[0].message.content


def _build(query: str, payload: dict) -> tuple[list[Condition], list[Clarification], list[str]]:
    """Validate one condition at a time so a single bad item is reported, not fatal."""
    haystack = _norm(query)
    conditions: list[Condition] = []
    problems: list[str] = []
    seen: set[str] = set()
    for i, raw in enumerate(payload.get("conditions") or []):
        try:
            c = Condition.model_validate(raw)
        except ValidationError as e:
            problems.append(f"condition {i} invalid: {e.errors()[0]['msg']}")
            continue
        if _norm(c.quote) not in haystack:
            problems.append(f"condition {i} quote {c.quote!r} is not verbatim in the request")
            continue
        if c.id in seen:
            continue
        seen.add(c.id)
        conditions.append(c)
    clarifications: list[Clarification] = []
    for raw in payload.get("clarifications") or []:
        try:
            clarifications.append(Clarification.model_validate(raw))
        except ValidationError:
            continue
    return conditions, clarifications, problems


def parse_conditions(
    query: str,
    *,
    complete: CompleteFn | None = None,
    run_id: str | None = None,
    max_attempts: int = 2,
) -> ConditionSet:
    """Parse `query`. On invalid output, retry once telling the model what was wrong;
    on the last attempt keep the valid conditions and drop the rest."""
    if not query or not query.strip():
        raise ConditionParseError("empty query")
    call = complete or (lambda s, u: _openai_complete(s, u, run_id=run_id))

    user = query
    last_error = "no attempt made"
    for attempt in range(1, max_attempts + 1):
        try:
            payload = json.loads(call(SYSTEM_PROMPT, user))
            if not isinstance(payload, dict):
                raise ValueError("top-level JSON is not an object")
        except (ValueError, TypeError) as e:
            last_error = f"invalid JSON: {e}"
            user = f"{query}\n\n[Your previous output was not valid JSON ({e}). Return the JSON object only.]"
            continue

        conditions, clarifications, problems = _build(query, payload)
        if problems and attempt < max_attempts:
            last_error = "; ".join(problems)
            user = f"{query}\n\n[Fix these problems and return the full JSON again: {last_error}]"
            continue
        if not conditions:
            last_error = "; ".join(problems) or "no conditions extracted"
            continue
        return ConditionSet(raw_query=query, conditions=conditions, clarifications=clarifications)

    raise ConditionParseError(last_error)
