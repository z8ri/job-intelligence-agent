"""
导出人工抽查用的 prompt 文件：把 24 条待抽查职位 + 分类规则组装成独立 markdown,
用户可直接喂给多个外部 LLM 做交叉验证。

用法:
    python -m src.classification.export_review_prompt              # 默认 24 条,seed=42
    python -m src.classification.export_review_prompt --sample 30
    python -m src.classification.export_review_prompt --all

输出:
    data/review_prompt.md    给 LLM 看的完整 prompt(规则 + 数据 + 输出格式)
    data/review_sample.json  本次抽样的 job_id 列表,供后续对比多 AI 答案用
"""

import argparse
import json
import random
import sys
from pathlib import Path

LABELED_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "labeled_jobs.json"
PROMPT_OUT = Path(__file__).resolve().parent.parent.parent / "data" / "review_prompt.md"
SAMPLE_OUT = Path(__file__).resolve().parent.parent.parent / "data" / "review_sample.json"

DESC_MAX_CHARS = 600

RULES_MD = """\
# Job Category Classification Task

Please classify each of the following job postings into exactly **ONE** of 7 categories. These postings are scraped from HackerNews "Who is Hiring" threads and public company ATS APIs, so formatting is messy and many single posts advertise multiple roles.

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

Output **ONLY** a JSON array in the exact order of the jobs below. Each entry has `job_id` and `category`. No explanation, no extra fields.

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
    parser = argparse.ArgumentParser(description="Export review prompt for external LLMs")
    parser.add_argument("--sample", type=int, default=24, help="sample size (default 24)")
    parser.add_argument("--all", action="store_true", help="export all jobs")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--batch-size", type=int, default=0,
                        help="if >0, split into multiple batched prompt files of this size")
    args = parser.parse_args()

    if not LABELED_PATH.exists():
        print(f"[error] {LABELED_PATH} not found.", file=sys.stderr)
        return 1

    with LABELED_PATH.open("r", encoding="utf-8") as f:
        labeled = json.load(f)
    n = len(labeled)

    if args.all:
        indices = list(range(n))
    else:
        k = min(args.sample, n)
        random.seed(args.seed)
        indices = sorted(random.sample(range(n), k))

    selected = [labeled[i] for i in indices]

    def _build_md(jobs_subset: list[dict], header_total: int) -> str:
        parts = [RULES_MD, f"## Jobs to classify ({len(jobs_subset)} total)\n"]
        for i, job in enumerate(jobs_subset, start=1):
            parts.append(format_job(i, job))
        return "\n".join(parts)

    if args.batch_size and args.batch_size > 0 and len(selected) > args.batch_size:
        n_batches = (len(selected) + args.batch_size - 1) // args.batch_size
        for b in range(n_batches):
            chunk = selected[b * args.batch_size : (b + 1) * args.batch_size]
            out_path = PROMPT_OUT.with_name(f"review_prompt_batch{b + 1}.md")
            out_path.write_text(_build_md(chunk, len(chunk)), encoding="utf-8")
            print(f"  batch {b + 1}: {len(chunk)} jobs → {out_path}")
        # 仍写一份总览的合并版（备用）
        PROMPT_OUT.write_text(_build_md(selected, len(selected)), encoding="utf-8")
    else:
        PROMPT_OUT.write_text(_build_md(selected, len(selected)), encoding="utf-8")

    sample_meta = {
        "seed": args.seed if not args.all else None,
        "total_in_file": n,
        "sample_size": len(selected),
        "job_ids": [j["job_id"] for j in selected],
        "llm_initial_labels": [
            {"job_id": j["job_id"], "category": j.get("category")} for j in selected
        ],
    }
    SAMPLE_OUT.write_text(json.dumps(sample_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Exported {len(selected)} jobs to:")
    print(f"  - {PROMPT_OUT}  (prompt for external LLMs)")
    print(f"  - {SAMPLE_OUT}  (sample metadata + current LLM labels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
