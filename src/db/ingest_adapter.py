"""
字段 adapter：把spider 的 data/structured_jobs.json 映射到 DB schema 格式。

Spider 输出字段与 DB schema 的差异：
- JSON 有 publish_time（ISO 8601 字符串），DB 列名相同但需 DATETIME 格式
- JSON remote 可能是 'remote_or_onsite'（spider 扩展值），DB enum 只有 remote/onsite/hybrid/unknown
- JSON 无 degree_req / category / crawled_at，用默认值兜底

用法:
    python -m src.db.ingest_adapter                          # 入库默认文件
    python -m src.db.ingest_adapter data/structured_jobs.json
"""

import json
import html
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from src.db.database import get_connection, insert_job

DEFAULT_INPUT = Path(__file__).resolve().parent.parent.parent / "data" / "structured_jobs.json"

REMOTE_REMAP = {
    "remote_or_onsite": "remote",
}
VALID_REMOTE = {"remote", "onsite", "hybrid", "unknown"}

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# Greenhouse 原始 slug（Stripe/Oklo/Coast）返回的岗位里大约 60% 是销售/业务/硬件
# 岗位（Account Executive、Mechanical Engineer 等），与我们 7 类软件分类体系
# 不匹配，会严重污染 TF-IDF 与分类器。入库前用 title 过滤到软件 / 数据 / 产品
# 设计这类"技术向岗位"。HN 数据本身就是 Who-is-Hiring 技术帖，不经过这个过滤器。
_SOFTWARE_TITLE_RE = re.compile(
    r"\b("
    r"software|backend|frontend|fullstack|full[\-\s]?stack|front[\-\s]?end|back[\-\s]?end|"
    r"devops|sre|site reliability|platform|infrastructure|infra|cloud|"
    r"data engineer|data scientist|data analyst|ml engineer|ai engineer|"
    r"applied scientist|research scientist|machine learning|"
    r"security engineer|mobile engineer|ios|android|"
    r"integration engineer|forward deployed|solutions engineer|sdk engineer|api engineer|"
    r"staff engineer|principal engineer|tech lead|engineering manager|"
    r"software architect|programmer|developer|"
    r"product designer|design engineer|product manager, (engineering|platform|developer|infrastructure|data|ml|ai)"
    r")\b",
    re.IGNORECASE,
)

# title 含下列词则视为非软件岗直接剔除（即便名字里含 Engineer）
_NON_SOFTWARE_TITLE_RE = re.compile(
    r"\b("
    r"mechanical|thermal|nuclear|reactor|radioactive|radiochemistry|"
    r"hardware test|fabrication|construction|hvac|industrial hygienist|"
    r"waste handling|mechatronics|civil engineer|structural engineer|"
    r"chemical engineer|environmental engineer|aerospace|"
    r"process controls|facility|physicist|"
    r"account executive|account manager|sales|marketing|bdr|"
    r"business development representative|"
    r"program manager|project manager|engagement manager|"
    r"recruiter|legal|counsel|compliance|privacy officer|"
    r"finance|accounting|audit|tax|admin|"
    r"customer (success|support)|community manager|communications manager|"
    r"content strategist|social media|"
    r"people (partner|consultant|operations)|"
    r"executive briefing|chief of staff"
    r")\b",
    re.IGNORECASE,
)


def is_target_role(title: str | None, source: str | None = None) -> bool:
    """是否保留此职位。HN 数据不过滤；Greenhouse/Lever 等 ATS 源走 title 白+黑名单。"""
    if source != "greenhouse" and source != "lever":
        return True
    if not title:
        return False
    if _NON_SOFTWARE_TITLE_RE.search(title):
        return False
    return bool(_SOFTWARE_TITLE_RE.search(title))


def _clean_description(text: str | None) -> str | None:
    """Greenhouse 原始 description 带 HTML 标签与 smart quotes；入库前剥净并 NFKC 规范化。"""
    if not text:
        return text
    s = html.unescape(text)
    s = _HTML_TAG_RE.sub(" ", s)
    s = unicodedata.normalize("NFKC", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _normalize_publish_time(value: str | None) -> str | None:
    """ISO 8601 'T' 分隔 → MySQL DATETIME 'YYYY-MM-DD HH:MM:SS'。"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _normalize_remote(value: str | None) -> str:
    if not value:
        return "unknown"
    v = value.strip().lower()
    v = REMOTE_REMAP.get(v, v)
    return v if v in VALID_REMOTE else "unknown"


def adapt_record(raw: dict) -> dict:
    """把spider 的 JSON dict 映射成 insert_job 期待的 dict。"""
    publish_time = _normalize_publish_time(raw.get("publish_time"))
    crawled_at = publish_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "job_id": raw["job_id"],
        "source": raw.get("source", "unknown"),
        "company": raw.get("company"),
        "title": raw.get("title"),
        "location": raw.get("location"),
        "remote": _normalize_remote(raw.get("remote")),
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "degree_req": "unknown",
        "category": "other",
        "description": _clean_description(raw.get("description")),
        "publish_time": publish_time,
        "crawled_at": crawled_at,
        "tags": raw.get("tags") or [],
    }


def ingest_structured_json(json_path: str | Path, **conn_overrides) -> int:
    """
    读取 spider 产出的 structured_jobs.json，做字段映射后批量入库。

    Returns:
        成功插入的记录数。
    """
    path = Path(json_path)
    with open(path, "r", encoding="utf-8") as f:
        raw_jobs = json.load(f)

    filtered = [r for r in raw_jobs if is_target_role(r.get("title"), r.get("source"))]
    dropped = len(raw_jobs) - len(filtered)

    conn = get_connection(**conn_overrides)
    inserted = 0
    try:
        for raw in filtered:
            adapted = adapt_record(raw)
            insert_job(conn, adapted)
            inserted += 1
        conn.commit()
    finally:
        conn.close()

    print(f"入库完成：{inserted} / {len(raw_jobs)} 条（过滤掉 {dropped} 条非软件岗）")
    return inserted


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_INPUT)
    ingest_structured_json(path)
