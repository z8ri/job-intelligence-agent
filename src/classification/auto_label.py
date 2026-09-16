"""
LLM-assisted job category labeling (training set generation).

Samples jobs from MySQL (stratified + random), classifies them into 7
categories with GPT-4o-mini, and writes data/labeled_jobs.json for
classifier.train().

Strategy:
- Stratified sampling: pre-filter a batch per category by title keywords so
  every category has training samples (categories with too few keyword hits
  are topped up randomly; the remaining quota is purely random).
- Keywords are only used for coverage; the category is decided by the LLM
  (avoids the leakage of "title contains backend => must be backend").
- Temperature=0.0, one prompt per job, output is a single category name.

Usage:
    python -m src.classification.auto_label              # default 120 jobs
    python -m src.classification.auto_label 150          # explicit count
    python -m src.classification.auto_label 120 --dry-run   # sample only, no LLM calls
"""

import json
import random
import sys
from pathlib import Path

from src.db.database import get_connection
from src.llm import MODEL, get_client

CATEGORIES = ["backend", "frontend", "data", "devops", "fullstack", "mobile", "management"]

OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "labeled_jobs.json"

PER_CATEGORY_QUOTA = 15
DESC_MAX_CHARS = 600

CATEGORY_KEYWORDS = {
    "backend": ["backend", "back-end", "server engineer", "api engineer",
                "distributed systems", "golang engineer", "python engineer"],
    "frontend": ["frontend", "front-end", "ui engineer", "react developer",
                 "vue developer", "web developer"],
    "data": ["data scientist", "data engineer", "machine learning",
             "ml engineer", "ai engineer", "analytics engineer", "nlp engineer"],
    "devops": ["devops", "sre", "site reliability", "platform engineer",
               "infrastructure", "cloud engineer"],
    "fullstack": ["fullstack", "full-stack", "full stack"],
    "mobile": ["ios ", "android ", "mobile engineer", "swift developer",
               "kotlin developer", "react native"],
    "management": ["engineering manager", "director of engineering",
                   "vp of engineering", "head of engineering", "cto",
                   "engineering lead", "tech lead"],
}

SYSTEM_PROMPT = """\
You are a job category classifier. Assign exactly ONE category from:
backend, frontend, data, devops, fullstack, mobile, management.

Category definitions:
- backend: server-side engineering (APIs, microservices, databases, distributed systems, backend platforms).
- frontend: client-side / browser development (UI components, UX, web apps, design systems).
- data: data science, data engineering, ML/AI research or engineering, analytics, NLP, computer vision.
- devops: infrastructure, SRE, DevOps, platform reliability, cloud ops, CI/CD, observability.
- fullstack: A SINGLE role that explicitly requires building BOTH frontend AND backend work. The same engineer writes React/Vue UI AND server-side APIs. NOT for multi-role "we are hiring X, Y, and Z" postings.
- mobile: iOS, Android, or cross-platform mobile (React Native, Flutter).
- management: engineering manager, director, VP, head-of-engineering, CTO — people managers of engineers.

Classification rules:
1. **Multi-role / aggregate postings (very common on HackerNews)**: titles like "Engineers (Backend, Frontend, Data, Mobile)" or "Backend + Data Engineer" list MULTIPLE distinct positions. Classify by the FIRST or MOST-EMPHASIZED role, NOT as fullstack. Examples:
   - "Backend + Data Engineer" → backend (backend listed first, and data is a separate role)
   - "SRE, data platform, backend engineers" → devops (SRE is first)
   - "Backend+AI focus" → backend (backend is the primary focus)
   - "Engineers (Backend, Frontend, Data)" → backend (first listed)
2. **Only use fullstack** when a single role description says the engineer personally builds both FE and UI AND backend/APIs (e.g. "Fullstack Engineer: build React UI and Node.js backend").
3. If the primary focus is ML / AI / data even with a "software engineer" title → data.
4. People managers of engineers → management (even if technical contributor is mentioned).
5. If a "senior engineer" title is generic but the description is backend-heavy → backend.
6. Prefer the closest fit when ambiguous; do not output any category outside the list.

Output ONLY the single category name in lowercase. No punctuation, no explanation.
"""

FEW_SHOT = [
    (
        "Title: Senior Backend Engineer\nTags: Python, PostgreSQL, AWS\n"
        "Description: Build and scale our API platform handling 10M+ requests/day. "
        "Own database schema design and query performance.",
        "backend",
    ),
    (
        "Title: ML Research Engineer\nTags: PyTorch, Transformers\n"
        "Description: Train large language models for our retrieval product. "
        "Experiment with novel architectures and publish findings.",
        "data",
    ),
    (
        "Title: Staff Frontend Engineer\nTags: React, TypeScript, Design Systems\n"
        "Description: Lead our component library and shape UX for millions of users.",
        "frontend",
    ),
    (
        "Title: Engineering Manager, Platform\nTags: Leadership\n"
        "Description: Manage a team of 8 backend engineers. Drive roadmap, mentor "
        "engineers, own platform reliability goals.",
        "management",
    ),
    (
        "Title: Fullstack Engineer\nTags: React, Node.js, TypeScript\n"
        "Description: You will own features end-to-end — design the UI in React, "
        "build the Node.js API that powers it, and ship to production.",
        "fullstack",
    ),
    (
        "Title: Backend + Data Engineer\nTags: Python, Kafka\n"
        "Description: We are hiring two roles: (1) a backend engineer to scale our "
        "services, and (2) a data engineer to build pipelines. Apply to either.",
        "backend",
    ),
    (
        "Title: Software Engineers (Backend, Frontend, Data, Mobile)\nTags: Various\n"
        "Description: We are hiring across multiple teams. Backend engineers will "
        "work on APIs; frontend engineers will build React UI; data engineers work "
        "on analytics pipelines; mobile engineers work on iOS/Android.",
        "backend",
    ),
]

_FEW_SHOT_MESSAGES: list[dict] = []
for _job_text, _cat in FEW_SHOT:
    _FEW_SHOT_MESSAGES.append({"role": "user", "content": _job_text})
    _FEW_SHOT_MESSAGES.append({"role": "assistant", "content": _cat})


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def _fetch_by_title_keywords(conn, keywords: list[str], limit: int, exclude_ids: set[str]) -> list[dict]:
    """Fetch a batch of jobs by title LIKE keywords, excluding already-sampled ids."""
    if not keywords:
        return []
    like_clauses = " OR ".join(["LOWER(title) LIKE %s"] * len(keywords))
    params = [f"%{kw.lower()}%" for kw in keywords]
    exclude_sql = ""
    if exclude_ids:
        placeholders = ",".join(["%s"] * len(exclude_ids))
        exclude_sql = f" AND job_id NOT IN ({placeholders})"
        params.extend(exclude_ids)

    sql = (
        f"SELECT job_id, title, company, description FROM jobs "
        f"WHERE ({like_clauses}) AND title IS NOT NULL AND title != 'Unknown' "
        f"AND description IS NOT NULL AND CHAR_LENGTH(description) > 80"
        f"{exclude_sql} "
        f"ORDER BY RAND() LIMIT {int(limit)}"
    )
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def _fetch_random(conn, limit: int, exclude_ids: set[str]) -> list[dict]:
    """Random fetch (excluding already-sampled ids)."""
    params: list = []
    exclude_sql = ""
    if exclude_ids:
        placeholders = ",".join(["%s"] * len(exclude_ids))
        exclude_sql = f" AND job_id NOT IN ({placeholders})"
        params = list(exclude_ids)

    sql = (
        f"SELECT job_id, title, company, description FROM jobs "
        f"WHERE title IS NOT NULL AND title != 'Unknown' "
        f"AND description IS NOT NULL AND CHAR_LENGTH(description) > 80"
        f"{exclude_sql} "
        f"ORDER BY RAND() LIMIT {int(limit)}"
    )
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def _fetch_tags(conn, job_ids: list[str]) -> dict[str, list[str]]:
    if not job_ids:
        return {}
    placeholders = ",".join(["%s"] * len(job_ids))
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT job_id, tag FROM job_tags WHERE job_id IN ({placeholders})",
            job_ids,
        )
        rows = cur.fetchall()
    tag_map: dict[str, list[str]] = {}
    for r in rows:
        tag_map.setdefault(r["job_id"], []).append(r["tag"])
    return tag_map


def sample_jobs(target_n: int = 120) -> list[dict]:
    """Stratified + random sampling of target_n jobs."""
    conn = get_connection()
    try:
        sampled: dict[str, dict] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            rows = _fetch_by_title_keywords(
                conn, keywords, limit=PER_CATEGORY_QUOTA, exclude_ids=set(sampled.keys())
            )
            for row in rows:
                sampled[row["job_id"]] = row
            print(f"  [{category}] keyword pre-filter hit {len(rows)} jobs (total {len(sampled)})")

        remaining = target_n - len(sampled)
        if remaining > 0:
            random_rows = _fetch_random(conn, limit=remaining, exclude_ids=set(sampled.keys()))
            for row in random_rows:
                sampled[row["job_id"]] = row
            print(f"  [random] topped up with {len(random_rows)} jobs (total {len(sampled)})")

        jobs = list(sampled.values())[:target_n]
        tag_map = _fetch_tags(conn, [j["job_id"] for j in jobs])
        for job in jobs:
            job["tags"] = tag_map.get(job["job_id"], [])
        return jobs
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# LLM labeling
# ---------------------------------------------------------------------------

def _format_job_for_llm(job: dict) -> str:
    title = job.get("title") or ""
    tags = job.get("tags") or []
    desc = (job.get("description") or "")[:DESC_MAX_CHARS]
    tags_str = ", ".join(tags) if tags else "(none)"
    return f"Title: {title}\nTags: {tags_str}\nDescription: {desc}"


def classify_one(job: dict, client) -> str | None:
    """Classify a single job via the LLM; returns the category name (None on failure)."""
    user_text = _format_job_for_llm(job)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_FEW_SHOT_MESSAGES,
        {"role": "user", "content": user_text},
    ]
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=10,
        )
        raw = resp.choices[0].message.content.strip().lower()
        raw = raw.strip(".,!?\"'` \n")
        if raw in CATEGORIES:
            return raw
        for cat in CATEGORIES:
            if cat in raw:
                return cat
        return None
    except Exception as e:
        print(f"    ! LLM call failed for {job.get('job_id')}: {e}")
        return None


def label_jobs(jobs: list[dict]) -> list[dict]:
    """Call the LLM on each sampled job; returns the labeled list with a category field."""
    client = get_client()
    labeled: list[dict] = []
    unknown = 0
    for i, job in enumerate(jobs, 1):
        cat = classify_one(job, client)
        if cat is None:
            unknown += 1
            continue
        labeled.append({
            "job_id": job["job_id"],
            "title": job.get("title"),
            "company": job.get("company"),
            "tags": job.get("tags") or [],
            "description": job.get("description"),
            "category": cat,
            "label_source": f"llm-{MODEL}",
        })
        if i % 10 == 0:
            print(f"  labeled {i}/{len(jobs)}")
    print(f"Done: {len(labeled)} succeeded, {unknown} failed")
    return labeled


# ---------------------------------------------------------------------------
# Output + summary
# ---------------------------------------------------------------------------

def write_labeled(labeled: list[dict], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False, indent=2)
    print(f"Wrote {path} ({len(labeled)} jobs)")


def print_category_distribution(labeled: list[dict]) -> None:
    counts: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    for job in labeled:
        counts[job["category"]] = counts.get(job["category"], 0) + 1
    print("\nCategory distribution:")
    for cat in CATEGORIES:
        print(f"  {cat:12s} {counts[cat]:3d}")


def main(target_n: int = 120, dry_run: bool = False) -> None:
    random.seed(42)
    print(f"Sampling target: {target_n} jobs")
    jobs = sample_jobs(target_n)
    print(f"Sampled {len(jobs)} jobs\n")

    if dry_run:
        print("=== dry-run: skipping LLM labeling, writing sampled jobs only ===")
        raw_path = OUTPUT_PATH.with_name("sampled_jobs_unlabeled.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2, default=str)
        print(f"Wrote {raw_path}")
        return

    print("Starting LLM labeling (GPT-4o-mini)...")
    labeled = label_jobs(jobs)
    write_labeled(labeled)
    print_category_distribution(labeled)
    print(f"\nNext: manually spot-check {max(20, len(labeled) // 5)} labels, then run "
          f"`python -m src.classification.classifier train`")


if __name__ == "__main__":
    args = sys.argv[1:]
    target = 120
    dry = False
    for a in args:
        if a == "--dry-run":
            dry = True
        elif a.isdigit():
            target = int(a)
    main(target_n=target, dry_run=dry)
