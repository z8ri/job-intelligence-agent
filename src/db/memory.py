"""Cross-turn preference memory: session_id -> last known full preference profile, persisted in MySQL.

"The current query overrides memory": when merging, fields explicitly mentioned in
this turn win, and only fields not mentioned fall back to the remembered values.
is_job_query / weight_adjustments / retrieval_mode / raw_response are per-turn
judgments, not stable preferences, so they are not inherited across turns. This
matters most for weight_adjustments, which is a one-off emphasis in the current
sentence and should not keep applying once the user stops mentioning it.
"""

import json

from src.db.database import get_connection

_MEMORY_FIELDS = [
    "description_keywords",
    "target_salary",
    "preferred_location",
    "remote_preference",
    "desired_tags",
    "preferred_category",
    "hard_filters",
]

_EMPTY_VALUES = (None, [], {}, "")


def load_memory(session_id: str) -> dict:
    """Return the last saved preference dict, or {} if there is no record."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT preferences FROM user_memory WHERE session_id=%s", (session_id,)
            )
            row = cur.fetchone()
        if not row:
            return {}
        return json.loads(row["preferences"])
    finally:
        conn.close()


def save_memory(session_id: str, preferences: dict) -> None:
    """Persist only the _MEMORY_FIELDS of the (merged) profile, overwriting any existing row."""
    payload = {k: preferences.get(k) for k in _MEMORY_FIELDS}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_memory (session_id, preferences)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE preferences=VALUES(preferences)
                """,
                (session_id, json.dumps(payload)),
            )
        conn.commit()
    finally:
        conn.close()


def merge_preferences(current: dict, memory: dict) -> dict:
    """Keep fields explicitly set this turn; fields left empty fall back to the remembered values.

    Fields outside _MEMORY_FIELDS (is_job_query/weight_adjustments/retrieval_mode/
    raw_response, etc.) are taken from current as-is, with no merging.
    """
    merged = dict(current)
    for field in _MEMORY_FIELDS:
        if current.get(field) in _EMPTY_VALUES and memory.get(field) not in _EMPTY_VALUES:
            merged[field] = memory[field]
    return merged
