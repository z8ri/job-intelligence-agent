"""
Field adapter: map the spider's data/structured_jobs.json onto the DB schema.

Differences between the spider output and the DB schema:
- JSON has publish_time as an ISO 8601 string; the DB column has the same name but needs DATETIME format
- JSON remote may be 'remote_or_onsite' (a spider extension); the DB enum only has remote/onsite/hybrid/unknown
- JSON has no degree_req / category / crawled_at; defaults are used as fallbacks

Usage:
    python -m src.db.ingest_adapter                          # ingest the default file
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

# Roughly 60% of the jobs returned by the raw Greenhouse slugs (Stripe/Oklo/Coast)
# are sales/business/hardware roles (Account Executive, Mechanical Engineer, etc.).
# They do not fit our 7-class software taxonomy and would badly pollute TF-IDF and
# the classifier, so we filter by title to software / data / product-design style
# "technical" roles before ingesting. HN data comes from Who-is-Hiring tech threads
# already and skips this filter.
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

# Titles containing any of these are treated as non-software and dropped (even if they say "Engineer")
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
    """Whether to keep this job. HN data is not filtered; ATS sources (Greenhouse/Lever) go through the title whitelist + blacklist."""
    if source != "greenhouse" and source != "lever":
        return True
    if not title:
        return False
    if _NON_SOFTWARE_TITLE_RE.search(title):
        return False
    return bool(_SOFTWARE_TITLE_RE.search(title))


def _clean_description(text: str | None) -> str | None:
    """Raw Greenhouse descriptions contain HTML tags and smart quotes; strip them and NFKC-normalize before ingesting."""
    if not text:
        return text
    s = html.unescape(text)
    s = _HTML_TAG_RE.sub(" ", s)
    s = unicodedata.normalize("NFKC", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _normalize_publish_time(value: str | None) -> str | None:
    """ISO 8601 with 'T' separator -> MySQL DATETIME 'YYYY-MM-DD HH:MM:SS'."""
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
    """Map a spider JSON dict onto the dict that insert_job expects."""
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
    Read the spider's structured_jobs.json, map the fields, and bulk-insert into the DB.

    Returns:
        Number of records inserted.
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

    print(f"Ingested {inserted} / {len(raw_jobs)} jobs ({dropped} non-software roles filtered out)")
    return inserted


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_INPUT)
    ingest_structured_json(path)
