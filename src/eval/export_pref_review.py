"""
§7.2 偏好提取准确率 — 导出三家 LLM 审查用 prompt

把 40 条查询 + 偏好字段规范（与 src/llm/query_understanding.py 完全一致）
打包到一份 markdown，用户可直接贴到 claude.ai / chatgpt.com / gemini.google.com。
三家 LLM 独立从原始查询提取偏好 JSON，多数投票当 gold。

用法:
    python -m src.eval.export_pref_review

输出:
    data/pref_extraction_review_prompt.md
"""

import json
import sys
from pathlib import Path

from src.llm.query_understanding import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_QUERIES_PATH = ROOT / "data" / "test_queries.json"
PROMPT_OUT = ROOT / "data" / "pref_extraction_review_prompt.md"

HEADER = """\
# Job Query Preference Extraction Task (Evaluation Set)

You are helping to evaluate a job-search system's query understanding module. For each user query below, independently extract a structured preference JSON following the schema and examples below. Do NOT look at or refer to any system-provided answer — your job is to produce your own best-effort extraction.

## Schema

"""

OUTPUT_SPEC = """\

## Output format

Output **ONLY** a single JSON array in the exact order of the queries below. Each entry MUST have `query_id` and `preferences` fields. No explanation, no extra text, no markdown fences.

```json
[
  {"query_id": "q01", "preferences": {"description_keywords": null, "target_salary": 150000, "preferred_location": null, "remote_preference": "remote", "desired_tags": ["Python"], "preferred_category": null, "weight_adjustments": {"salary": "high", "remote": "high"}, "hard_filters": []}},
  {"query_id": "q02", "preferences": {...}}
]
```

---

"""


def build_few_shot_section() -> str:
    lines = ["## Examples\n"]
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, start=1):
        lines.append(f"**Example {i}**")
        lines.append(f"- Query: `{ex['query']}`")
        lines.append(f"- Output:")
        lines.append("```json")
        lines.append(json.dumps(ex["output"], ensure_ascii=False))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not TEST_QUERIES_PATH.exists():
        print(f"[error] {TEST_QUERIES_PATH} not found", file=sys.stderr)
        return 1

    with TEST_QUERIES_PATH.open("r", encoding="utf-8") as f:
        queries = json.load(f)

    parts = [HEADER, SYSTEM_PROMPT, "\n", build_few_shot_section(), OUTPUT_SPEC]
    parts.append(f"## Queries to process ({len(queries)} total)\n")
    for q in queries:
        parts.append(f"### {q['id']}")
        parts.append(f"> {q['query']}")
        parts.append("")

    PROMPT_OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"已导出 {len(queries)} 条查询到 {PROMPT_OUT}")
    print()
    print("下一步：把该文件整份内容贴到：")
    print("  - claude.ai          → 保存回复到 data/reviews_pref/claude.json")
    print("  - chatgpt.com        → 保存回复到 data/reviews_pref/chatgpt.json")
    print("  - gemini.google.com  → 保存回复到 data/reviews_pref/gemini.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
