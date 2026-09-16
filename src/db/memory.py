"""跨轮偏好记忆：session_id -> 上次已知的完整偏好画像，持久化在 MySQL。

"当前查询覆盖历史记忆"：合并时以本轮明确提到的字段为准，本轮没提的字段才
回退到记忆里的值。is_job_query / weight_adjustments / retrieval_mode /
raw_response 这几个是"当场判断"，不是稳定偏好，不参与跨轮继承——尤其是
weight_adjustments，是"这句话里临时强调"，不该在用户没再提的情况下一直生效。
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
    """返回上次保存的偏好 dict；没有记录返回 {}。"""
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
    """只挑 _MEMORY_FIELDS 里的字段落库（合并后的画像），覆盖写入。"""
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
    """本轮明确提到的字段保留；本轮没提（值为空）的字段回退到记忆里的值。

    非 _MEMORY_FIELDS 字段（is_job_query/weight_adjustments/retrieval_mode/
    raw_response 等）原样用 current 的，不做任何合并。
    """
    merged = dict(current)
    for field in _MEMORY_FIELDS:
        if current.get(field) in _EMPTY_VALUES and memory.get(field) not in _EMPTY_VALUES:
            merged[field] = memory[field]
    return merged
