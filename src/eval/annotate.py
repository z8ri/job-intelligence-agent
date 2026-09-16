"""
DEPRECATED for the main evaluation flow — it annotates unsorted DB rows, which
is NOT a pooled evaluation and biases nothing meaningful.

For main flow use `src.eval.pool_eval` (pools top-10 across all 10 configs,
then rates via gpt-4o-mini). Kept here only as a fallback if we ever want to
hand-grade a small slice.
"""

import sys

from src.db.database import load_candidates
from src.eval import load_test_queries, save_test_queries


def display_job(job: dict, index: int) -> None:
    """Display a job for annotation."""
    print(f"\n--- Job {index + 1} ---")
    print(f"  ID:       {job.get('job_id', 'N/A')}")
    print(f"  Company:  {job.get('company', 'N/A')}")
    print(f"  Title:    {job.get('title', 'N/A')}")
    print(f"  Location: {job.get('location', 'N/A')}")
    print(f"  Remote:   {job.get('remote', 'N/A')}")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    if salary_min or salary_max:
        print(f"  Salary:   ${salary_min or '?':,} - ${salary_max or '?':,}")
    tags = job.get("tags", [])
    if tags:
        print(f"  Tags:     {', '.join(tags)}")
    print(f"  Category: {job.get('category', 'N/A')}")
    desc = job.get("description", "")
    if desc:
        print(f"  Desc:     {desc[:200]}...")


def annotate_query(query: dict, candidates: list[dict], top_k: int = 10) -> list[int]:
    """
    Interactive annotation for a single query.

    Returns:
        list of relevance grades (0/1/2) for the first top_k candidates
    """
    print(f"\n{'=' * 60}")
    print(f"Query [{query['id']}]: {query['query']}")
    print(f"{'=' * 60}")

    shown = candidates[:top_k]
    annotations = []

    for i, job in enumerate(shown):
        display_job(job, i)
        while True:
            grade = input("  Relevance (0=not relevant, 1=partial, 2=highly relevant, s=skip query): ").strip()
            if grade == "s":
                return []
            if grade in ("0", "1", "2"):
                annotations.append(int(grade))
                break
            print("  Invalid input. Enter 0, 1, 2, or s.")

    return annotations


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Annotate relevance for test queries")
    parser.add_argument("--query", type=str, default=None, help="Annotate specific query ID")
    parser.add_argument("--top-k", type=int, default=10, help="Number of candidates to show")
    args = parser.parse_args()

    queries = load_test_queries()

    # Load all candidates from DB
    print("Loading candidate jobs from the database...")
    try:
        all_candidates = load_candidates()
    except Exception as e:
        print(f"Could not connect to the database: {e}")
        print("Make sure MySQL is running and the data has been ingested.")
        sys.exit(1)

    if not all_candidates:
        print("No job data in the database. Run database.py ingest first.")
        sys.exit(1)

    print(f"Loaded {len(all_candidates)} candidate jobs\n")

    annotated_count = 0
    for query in queries:
        if args.query and query["id"] != args.query:
            continue

        # Skip already annotated
        if query.get("relevance_annotations"):
            print(f"[{query['id']}] already annotated, skipping")
            continue

        annotations = annotate_query(query, all_candidates, top_k=args.top_k)
        if annotations:
            query["relevance_annotations"] = annotations
            annotated_count += 1
            save_test_queries(queries)
            print(f"  -> saved {len(annotations)} annotations")

    print(f"\nAnnotation complete: {annotated_count} queries annotated this run")


if __name__ == "__main__":
    main()
