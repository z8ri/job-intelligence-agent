"""
Database module: connection management, schema setup, ingestion, and query helpers.

Connects to MySQL via pymysql.
"""

import json
import os
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

# Default connection parameters; can be overridden via environment variables
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", 3306)),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "job_intelligence"),
    "charset": "utf8mb4",
}

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
FILTERABLE_FIELDS = frozenset({"degree_req", "remote", "category", "source"})


def get_connection(**overrides):
    """Open a database connection."""
    config = {**DB_CONFIG, **overrides}
    return pymysql.connect(**config, cursorclass=DictCursor)


def init_db(**conn_overrides):
    """Run schema.sql to create the database and tables."""
    # Connect without a database first (it may not exist yet)
    config = {**DB_CONFIG, **conn_overrides}
    config.pop("database", None)
    conn = pymysql.connect(**config, cursorclass=DictCursor)

    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    try:
        with conn.cursor() as cur:
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    cur.execute(statement)
        conn.commit()
    finally:
        conn.close()


def insert_job(conn, job: dict):
    """
    Insert a single job record.

    job format (structured dict produced by the spider):
    {
        "job_id": "hn_12345",
        "source": "hackernews",
        "company": "Stripe",
        "title": "Backend Engineer",
        "location": "San Francisco, CA",
        "remote": "remote",
        "salary_min": 150000,
        "salary_max": 200000,
        "tags": ["Python", "AWS"],
        "description": "We are looking for...",
        "degree_req": "unknown",
        "category": "other",
        "crawled_at": "2025-04-15 12:00:00"
    }
    """
    sql_job = """
        INSERT INTO jobs (job_id, source, company, title, location, remote,
                          salary_min, salary_max, degree_req, category, description,
                          publish_time, crawled_at)
        VALUES (%(job_id)s, %(source)s, %(company)s, %(title)s, %(location)s, %(remote)s,
                %(salary_min)s, %(salary_max)s, %(degree_req)s, %(category)s, %(description)s,
                %(publish_time)s, %(crawled_at)s)
        ON DUPLICATE KEY UPDATE
            company=VALUES(company), title=VALUES(title), location=VALUES(location),
            remote=VALUES(remote), salary_min=VALUES(salary_min), salary_max=VALUES(salary_max),
            degree_req=VALUES(degree_req), category=VALUES(category),
            description=VALUES(description),
            publish_time=VALUES(publish_time), crawled_at=VALUES(crawled_at)
    """

    sql_tag = "INSERT IGNORE INTO job_tags (job_id, tag) VALUES (%s, %s)"

    row = {
        "job_id": job["job_id"],
        "source": job.get("source", "unknown"),
        "company": job.get("company"),
        "title": job.get("title"),
        "location": job.get("location"),
        "remote": job.get("remote", "unknown"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "degree_req": job.get("degree_req", "unknown"),
        "category": job.get("category", "other"),
        "description": job.get("description"),
        "publish_time": job.get("publish_time"),
        "crawled_at": job.get("crawled_at"),
    }

    with conn.cursor() as cur:
        cur.execute(sql_job, row)
        tags = job.get("tags") or []
        if tags:
            cur.executemany(sql_tag, [(job["job_id"], t) for t in tags])


def ingest_json(json_path: str, **conn_overrides):
    """
    Bulk ingest: read the JSON file produced by the spider and write it to MySQL.

    JSON file format: a list of job dicts [{ ... }, { ... }, ...]
    """
    with open(json_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    conn = get_connection(**conn_overrides)
    try:
        for job in jobs:
            insert_job(conn, job)
        conn.commit()
        print(f"Ingested {len(jobs)} jobs")
    finally:
        conn.close()


def load_candidates(hard_filters: list[dict] | None = None, **conn_overrides) -> list[dict]:
    """
    Load candidate jobs, with optional hard filters.

    hard_filters format (output of the LLM query-understanding step):
    [{"field": "degree_req", "exclude": ["phd", "master"]}]

    Returns a list of job dicts, each with every column of the jobs table plus a tags list.
    """
    conn = get_connection(**conn_overrides)
    try:
        where_clauses = []
        params = []

        if hard_filters:
            for f in hard_filters:
                field = f.get("field", "")
                if field not in FILTERABLE_FIELDS:
                    continue
                exclude = f.get("exclude", [])
                if exclude:
                    placeholders = ",".join(["%s"] * len(exclude))
                    where_clauses.append(f"`{field}` NOT IN ({placeholders})")
                    params.extend(exclude)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        sql = f"SELECT * FROM jobs WHERE {where_sql}"

        with conn.cursor() as cur:
            cur.execute(sql, params)
            jobs = cur.fetchall()

        if jobs:
            job_ids = [j["job_id"] for j in jobs]
            placeholders = ",".join(["%s"] * len(job_ids))
            with conn.cursor() as cur:
                cur.execute(f"SELECT job_id, tag FROM job_tags WHERE job_id IN ({placeholders})", job_ids)
                tag_rows = cur.fetchall()

            tag_map = {}
            for row in tag_rows:
                tag_map.setdefault(row["job_id"], []).append(row["tag"])

            for job in jobs:
                job["tags"] = tag_map.get(job["job_id"], [])

        return jobs
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python database.py init          # create database and tables")
        print("  python database.py ingest <file>  # import JSON data")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        init_db()
        print("Database initialized")
    elif cmd == "ingest" and len(sys.argv) >= 3:
        ingest_json(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
