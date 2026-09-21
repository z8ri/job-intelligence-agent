"""
LLM structured query understanding (pre-processing stage).

Converts the user's natural-language query into a structured preference JSON
for the scoring engine. The LLM only extracts preferences; it takes no part in
retrieval or ranking.
"""

import json

from src.llm import MODEL, get_client
from src.observability import log_call, timed_call
MAX_RETRIES = 2

SYSTEM_PROMPT = """\
You are a job search query understanding assistant. Extract structured preferences from the user's natural language query.

Output a JSON object with these fields (set to null if not mentioned):

- is_job_query: boolean. True if the user is genuinely asking about a job / career / role search (even when vague like "find me a job" or "remote work please"). False for greetings ("hi", "hello", "你好"), weather, math, generic chitchat, or anything unrelated to finding tech jobs. When false, all other fields may be null/empty — we will skip retrieval and respond with a polite refusal.
- description_keywords: list of keywords describing the desired role/responsibilities (e.g. ["machine learning", "distributed systems"])
- target_salary: target annual salary as integer in USD (e.g. 150000)
- preferred_location: preferred work location as a city/region string (e.g. "New York")
- remote_preference: one of "remote", "hybrid", "onsite", or null
- desired_tags: list of desired technology/skill tags (e.g. ["Python", "AWS", "React"])
- preferred_category: one of "backend", "frontend", "data", "devops", "fullstack", "mobile", "management", or null
- weight_adjustments: dict mapping field names to importance level ("high", "medium", "low") for fields the user emphasizes. Only include fields the user explicitly cares about more or less than usual.
- hard_filters: list of absolute constraints that MUST be met (e.g. [{"field": "degree_req", "exclude": ["phd", "master"]}]). Use sparingly — only for deal-breakers like degree requirements.
- retrieval_mode: one of "exact", "semantic", "exploratory", or null.
  - "exact": query has precise, specific technical terms (tech stack names, exact role titles) — literal keyword matching works well.
  - "semantic": query describes responsibilities/role in natural language that may not literally appear in job text, but still has clear intent.
  - "exploratory": query is vague or underspecified (e.g. "find me a job", no specific skills/role) — needs the broadest recall.

Output ONLY valid JSON. No explanation, no markdown fences."""

FEW_SHOT_EXAMPLES = [
    {
        "query": "Remote Python jobs above 150k",
        "output": {
            "description_keywords": None,
            "target_salary": 150000,
            "preferred_location": None,
            "remote_preference": "remote",
            "desired_tags": ["Python"],
            "preferred_category": None,
            "weight_adjustments": {"salary": "high", "remote": "high"},
            "hard_filters": [],
            "retrieval_mode": "exact"
        }
    },
    {
        "query": "ML roles near New York, ideally over 120k",
        "output": {
            "description_keywords": ["machine learning"],
            "target_salary": 120000,
            "preferred_location": "New York",
            "remote_preference": None,
            "desired_tags": ["Machine Learning"],
            "preferred_category": "data",
            "weight_adjustments": {"location": "high", "salary": "medium"},
            "hard_filters": [],
            "retrieval_mode": "semantic"
        }
    },
    {
        "query": "Junior dev positions, no PhD required",
        "output": {
            "description_keywords": ["junior", "entry level"],
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": None,
            "desired_tags": None,
            "preferred_category": None,
            "weight_adjustments": {},
            "hard_filters": [{"field": "degree_req", "exclude": ["phd"]}]
        }
    },
    {
        "query": "Senior backend engineer in San Francisco, React and Node.js, hybrid preferred, around 180k",
        "output": {
            "description_keywords": ["senior", "backend engineer"],
            "target_salary": 180000,
            "preferred_location": "San Francisco",
            "remote_preference": "hybrid",
            "desired_tags": ["React", "Node.js"],
            "preferred_category": "backend",
            "weight_adjustments": {},
            "hard_filters": []
        }
    },
    {
        "query": "Data engineering jobs with Spark and Kafka, salary doesn't matter much but must be remote",
        "output": {
            "description_keywords": ["data engineering"],
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": "remote",
            "desired_tags": ["Spark", "Kafka"],
            "preferred_category": "data",
            "weight_adjustments": {"remote": "high", "salary": "low"},
            "hard_filters": []
        }
    },
    {
        "query": "Frontend developer roles, React or Vue, anywhere in Texas",
        "output": {
            "description_keywords": ["frontend developer"],
            "target_salary": None,
            "preferred_location": "Texas",
            "remote_preference": None,
            "desired_tags": ["React", "Vue"],
            "preferred_category": "frontend",
            "weight_adjustments": {"location": "high"},
            "hard_filters": []
        }
    },
    {
        "query": "DevOps roles with AWS and Kubernetes, at least 140k, prefer onsite in Seattle",
        "output": {
            "description_keywords": ["devops"],
            "target_salary": 140000,
            "preferred_location": "Seattle",
            "remote_preference": "onsite",
            "desired_tags": ["AWS", "Kubernetes"],
            "preferred_category": "devops",
            "weight_adjustments": {"salary": "high"},
            "hard_filters": []
        }
    },
    {
        "query": "I want a management position, fully remote, good pay",
        "output": {
            "description_keywords": ["management", "engineering manager"],
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": "remote",
            "desired_tags": None,
            "preferred_category": "management",
            "weight_adjustments": {"remote": "high", "salary": "medium"},
            "hard_filters": [],
            "retrieval_mode": "semantic"
        }
    },
    # Single technical keyword → still a job query; extract as desired_tag.
    {
        "query": "python",
        "output": {
            "is_job_query": True,
            "description_keywords": None,
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": None,
            "desired_tags": ["Python"],
            "preferred_category": None,
            "weight_adjustments": {},
            "hard_filters": [],
            "retrieval_mode": "exact"
        }
    },
    # "highest paying" / "best pay" → very high target_salary so the salary
    # score naturally ranks higher-paying jobs first.
    {
        "query": "Highest paying Go developer positions",
        "output": {
            "description_keywords": ["Go developer"],
            "target_salary": 999999,
            "preferred_location": None,
            "remote_preference": None,
            "desired_tags": ["Go"],
            "preferred_category": None,
            "weight_adjustments": {"salary": "high"},
            "hard_filters": [],
            "retrieval_mode": "exact"
        }
    },
    # --- Negative examples: not job queries, should be rejected upstream ---
    {
        "query": "你好",
        "output": {
            "is_job_query": False,
            "description_keywords": None,
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": None,
            "desired_tags": None,
            "preferred_category": None,
            "weight_adjustments": {},
            "hard_filters": []
        }
    },
    {
        "query": "What's the weather in New York today?",
        "output": {
            "is_job_query": False,
            "description_keywords": None,
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": None,
            "desired_tags": None,
            "preferred_category": None,
            "weight_adjustments": {},
            "hard_filters": []
        }
    },
    {
        "query": "1 + 1 = ?",
        "output": {
            "is_job_query": False,
            "description_keywords": None,
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": None,
            "desired_tags": None,
            "preferred_category": None,
            "weight_adjustments": {},
            "hard_filters": []
        }
    },
    # --- Edge case: vague but still a job intent → keep going ---
    {
        "query": "find me a job please",
        "output": {
            "is_job_query": True,
            "description_keywords": None,
            "target_salary": None,
            "preferred_location": None,
            "remote_preference": None,
            "desired_tags": None,
            "preferred_category": None,
            "weight_adjustments": {},
            "hard_filters": [],
            "retrieval_mode": "exploratory"
        }
    }
]

VALID_FIELDS = {
    "is_job_query": (bool,),
    "description_keywords": (list, type(None)),
    "target_salary": (int, type(None)),
    "preferred_location": (str, type(None)),
    "remote_preference": (str, type(None)),
    "desired_tags": (list, type(None)),
    "preferred_category": (str, type(None)),
    "weight_adjustments": (dict,),
    "hard_filters": (list,),
    "retrieval_mode": (str, type(None)),
}

# "unknown" is a DB-level default, not a valid LLM output value
VALID_REMOTE = {"remote", "hybrid", "onsite"}
VALID_CATEGORY = {"backend", "frontend", "data", "devops", "fullstack", "mobile", "management"}
VALID_WEIGHT_FIELDS = {"description", "salary", "location", "remote", "tags", "category"}
VALID_IMPORTANCE = {"high", "medium", "low"}
VALID_RETRIEVAL_MODE = {"exact", "semantic", "exploratory"}

IMPORTANCE_MULTIPLIER = {
    "high": 2.0,
    "medium": 1.0,
    "low": 0.5,
}

DEFAULT_WEIGHTS = {
    "description": 0.35,
    "salary": 0.20,
    "location": 0.15,
    "remote": 0.10,
    "tags": 0.10,
    "category": 0.10,
}


_CACHED_FEW_SHOT_MESSAGES: list[dict] = []
for _ex in FEW_SHOT_EXAMPLES:
    # Pre-existing positive examples don't carry is_job_query; default to True.
    _output = {**_ex["output"]}
    _output.setdefault("is_job_query", True)
    # Examples not hand-annotated with a retrieval_mode fall back to the
    # middle-ground default ("semantic") rather than leaving it unset.
    _output.setdefault("retrieval_mode", "semantic")
    _CACHED_FEW_SHOT_MESSAGES.append({"role": "user", "content": _ex["query"]})
    _CACHED_FEW_SHOT_MESSAGES.append({"role": "assistant", "content": json.dumps(_output)})


def _build_messages(user_query: str, error_feedback: str | None = None) -> list[dict]:
    """Build the message list sent to the LLM."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_CACHED_FEW_SHOT_MESSAGES)
    messages.append({"role": "user", "content": user_query})

    if error_feedback:
        messages.append({
            "role": "user",
            "content": f"Your previous output had errors:\n{error_feedback}\nPlease fix and output valid JSON only."
        })

    return messages


def _validate_preferences(data: dict) -> list[str]:
    """Validate the structure and types of the preference JSON; return a list of errors."""
    errors = []

    for field, valid_types in VALID_FIELDS.items():
        if field not in data:
            errors.append(f"Missing field: {field}")
            continue
        val = data[field]
        if not isinstance(val, valid_types):
            errors.append(f"Field '{field}' has wrong type: expected {valid_types}, got {type(val).__name__}")

    if data.get("remote_preference") and data["remote_preference"] not in VALID_REMOTE:
        errors.append(f"Invalid remote_preference: '{data['remote_preference']}'. Must be one of {VALID_REMOTE}")

    if data.get("preferred_category") and data["preferred_category"] not in VALID_CATEGORY:
        errors.append(f"Invalid preferred_category: '{data['preferred_category']}'. Must be one of {VALID_CATEGORY}")

    if data.get("retrieval_mode") and data["retrieval_mode"] not in VALID_RETRIEVAL_MODE:
        errors.append(f"Invalid retrieval_mode: '{data['retrieval_mode']}'. Must be one of {VALID_RETRIEVAL_MODE}")

    if isinstance(data.get("weight_adjustments"), dict):
        for k, v in data["weight_adjustments"].items():
            if k not in VALID_WEIGHT_FIELDS:
                errors.append(f"Invalid weight field: '{k}'. Must be one of {VALID_WEIGHT_FIELDS}")
            if v not in VALID_IMPORTANCE:
                errors.append(f"Invalid importance for '{k}': '{v}'. Must be one of {VALID_IMPORTANCE}")

    if isinstance(data.get("target_salary"), int) and data["target_salary"] < 0:
        errors.append("target_salary cannot be negative")

    return errors


def compute_weights(weight_adjustments: dict) -> dict[str, float]:
    """
    Apply weight_adjustments to the default weights and normalize.

    The caller is responsible for filtering to fields that have a target value
    before calling this. This function only handles the importance -> multiplier
    mapping and normalization.
    """
    weights = dict(DEFAULT_WEIGHTS)

    for field, importance in weight_adjustments.items():
        if field in weights and importance in IMPORTANCE_MULTIPLIER:
            weights[field] *= IMPORTANCE_MULTIPLIER[importance]

    # Normalize
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}

    return weights


def parse_preferences(user_query: str, api_key: str | None = None, run_id: str | None = None) -> dict:
    """
    Main entry point: convert the user's natural-language query into a structured preference JSON.

    Args:
        user_query: the user's natural-language query
        api_key: OpenAI API key; falls back to the OPENAI_API_KEY env var if omitted
        run_id: pipeline run identifier, threaded through to the observability trace

    Returns:
        A dict with preferences and weights:
        {
            "preferences": { ... preference fields ... },
            "weights": { ... normalized weights ... },
            "raw_response": "raw LLM output"
        }

    Raises:
        ValueError: no valid JSON obtained after all retries
    """
    client = get_client(api_key)

    error_feedback = None
    last_raw = None

    for attempt in range(1 + MAX_RETRIES):
        messages = _build_messages(user_query, error_feedback)

        try:
            with timed_call() as t:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=512,
                )
        except Exception as e:
            log_call(run_id, "query_understanding", MODEL, t.elapsed_ms, success=False, error=str(e))
            raise
        usage = response.usage
        log_call(
            run_id, "query_understanding", MODEL, t.elapsed_ms,
            prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
        )

        raw = response.choices[0].message.content.strip()
        last_raw = raw

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            error_feedback = f"Invalid JSON: {e}"
            continue

        errors = _validate_preferences(data)
        if errors:
            error_feedback = "\n".join(errors)
            continue

        # Validation passed
        weight_adj = data.get("weight_adjustments", {})
        weights = compute_weights(weight_adj)

        return {
            "preferences": data,
            "weights": weights,
            "raw_response": last_raw,
        }

    log_call(run_id, "query_understanding", MODEL, 0.0, success=False, error=f"exhausted retries: {error_feedback}")
    raise ValueError(
        f"Failed to get valid preferences after {1 + MAX_RETRIES} attempts. "
        f"Last error: {error_feedback}\nLast response: {last_raw}"
    )
