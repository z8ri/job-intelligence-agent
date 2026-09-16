"""
§7.3 分类准确率 — 导出三家 LLM 审查用 prompt

读取 data/eval_results/classification_test_set.json（63 条测试职位），
生成 data/classification_review_prompt.md，用户可直接贴到 claude.ai /
chatgpt.com / gemini.google.com 获取三家独立分类结果。

用法:
    python -m src.eval.export_class_review

输出:
    data/classification_review_prompt.md
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_SET_PATH = ROOT / "data" / "eval_results" / "classification_test_set.json"
PROMPT_OUT = ROOT / "data" / "classification_review_prompt.md"

DESC_MAX_CHARS = 600

# 规则与训练集标注保持完全一致，保证可比性。
RULES_MD = """\
# Job Category Classification Task (Evaluation Set)

You are helping to evaluate a job-classification system. Please classify each of the following job postings into exactly **ONE** of 7 categories. These are real postings scraped from HackerNews "Who is Hiring" threads, so formatting is messy and many single posts advertise multiple roles.

## Categories

- **backend**: server-side engineering (APIs, microservices, databases, distributed systems, backend platforms).
- **frontend**: client-side / browser development (UI components, UX, web apps, design systems).
- **data**: data science, data engineering, ML / AI research or engineering, analytics, NLP, computer vision.
- **devops**: infrastructure, SRE, DevOps, platform reliability, cloud ops, CI/CD, observability.
- **fullstack**: A SINGLE role that explicitly requires the SAME engineer to build BOTH frontend UI AND backend APIs (e.g. "Fullstack Engineer: build React UI and Node.js backend"). NOT for multi-role "we're hiring frontend AND backend engineers" postings.
- **mobile**: iOS, Android, or cross-platform mobile (React Native, Flutter).
- **management**: engineering manager, director, VP, head-of-engineering, CTO — people managers of engineers.

## Classification rules

1. **Multi-role / aggregate postings (very common on HackerNews)**: titles like "Engineers (Backend, Frontend, Data, Mobile)" or "Backend + Data Engineer" list MULTIPLE distinct positions. Classify by the **FIRST or MOST-EMPHASIZED** role, **NOT as fullstack**. Examples:
   - "Backend + Data Engineer" → **backend** (backend listed first, data is a separate role)
   - "SRE, data platform, backend engineers" → **devops** (SRE is first)
   - "Backend+AI focus" → **backend** (backend is primary focus)
   - "Engineers (Backend, Frontend, Data)" → **backend** (first listed)
2. **Only use `fullstack`** when a single role description says the engineer personally builds both FE/UI AND backend/APIs. If the post lists frontend and backend as separate positions, pick the first one, NOT fullstack.
3. If the primary focus is ML / AI / data even with a generic "software engineer" title → **data**.
4. People managers of engineers → **management** (even if some individual-contributor technical work is mentioned).
5. If a "senior engineer" title is generic but the description is backend-heavy → **backend**.
6. Prefer the closest fit when ambiguous; do not invent categories outside the 7 listed.

## Output format

Output **ONLY** a JSON array in the exact order of the jobs below. Each entry has `job_id` and `category`. No explanation, no extra fields, no markdown fences.

```json
[
  {"job_id": "hn_XXX", "category": "backend"},
  {"job_id": "hn_YYY", "category": "data"}
]
```

---
"""


def truncate_desc(desc: str, limit: int = DESC_MAX_CHARS) -> str:
    desc = (desc or "").strip().replace("\n", " ")
    if len(desc) > limit:
        desc = desc[:limit].rstrip() + "..."
    return desc


def format_job(i: int, job: dict) -> str:
    tags = ", ".join(job.get("tags") or []) or "(no tags)"
    return (
        f"### Job {i} — job_id: `{job.get('job_id')}`\n"
        f"- **Title**: {job.get('title')}\n"
        f"- **Company**: {job.get('company')}\n"
        f"- **Tags**: {tags}\n"
        f"- **Description**: {truncate_desc(job.get('description', ''))}\n"
    )


def main() -> int:
    if not TEST_SET_PATH.exists():
        print(f"[error] {TEST_SET_PATH} not found. 先跑 `python -m src.eval.sample_class_test_set`", file=sys.stderr)
        return 1

    with TEST_SET_PATH.open("r", encoding="utf-8") as f:
        jobs = json.load(f)

    parts = [RULES_MD, f"## Jobs to classify ({len(jobs)} total)\n"]
    for i, job in enumerate(jobs, start=1):
        parts.append(format_job(i, job))

    PROMPT_OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"已导出 {len(jobs)} 条到 {PROMPT_OUT}")
    print()
    print("下一步：把该文件整份内容贴到：")
    print("  - claude.ai       → 保存回复到 data/reviews_class/claude.json")
    print("  - chatgpt.com     → 保存回复到 data/reviews_class/chatgpt.json")
    print("  - gemini.google.com → 保存回复到 data/reviews_class/gemini.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
