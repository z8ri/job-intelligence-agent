"""Evaluation utilities."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_QUERIES_PATH = PROJECT_ROOT / "data" / "test_queries.json"


def load_test_queries() -> list[dict]:
    with open(TEST_QUERIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_test_queries(queries: list[dict]) -> None:
    with open(TEST_QUERIES_PATH, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)
