"""
LLM 回答生成模块（后处理阶段）

将评分引擎排好序的 top-K 结果 + 用户原始问题送入 LLM，
生成结构化自然语言回答。LLM 不影响排序结果。
"""

import json

from src.llm import MODEL, get_client

SYSTEM_PROMPT = """\
You are a job search assistant. The user asked a question about jobs, and a retrieval system has already found and ranked the best matching positions.

Your task: present the top results as a clear, helpful natural language answer.

Rules:
1. Present jobs in the order given (they are already ranked by relevance).
2. For each job, highlight WHY it matches the user's query — mention the specific dimensions (salary fit, location proximity, tech stack overlap, remote match, etc.) based on the score breakdown provided.
3. Format: use a numbered list. For each job include company, title, key matching details, and a brief note on any tradeoffs (e.g. "salary slightly below target but strong tech stack match").
4. End with a brief summary comparing the top picks.
5. If no results are provided, say so honestly and suggest broadening the search.
6. Keep it concise — no filler, no generic career advice.
7. Respond in the same language as the user's query.
8. If a result has a "Verification note", honestly mention that caveat in its tradeoff line — don't treat it as if fully confirmed."""


def _format_job_for_prompt(job: dict, rank: int) -> str:
    """将单个职位及其评分格式化为 prompt 中的条目。"""
    lines = [f"### Result #{rank}"]
    lines.append(f"- Company: {job.get('company', 'N/A')}")
    lines.append(f"- Title: {job.get('title', 'N/A')}")
    lines.append(f"- Location: {job.get('location', 'N/A')}")
    lines.append(f"- Remote: {job.get('remote', 'unknown')}")

    sal_min = job.get("salary_min")
    sal_max = job.get("salary_max")
    if sal_min and sal_max:
        lines.append(f"- Salary: ${sal_min:,} - ${sal_max:,}")
    elif sal_min:
        lines.append(f"- Salary: ${sal_min:,}+")
    elif sal_max:
        lines.append(f"- Salary: up to ${sal_max:,}")
    else:
        lines.append("- Salary: not specified")

    tags = job.get("tags", [])
    if tags:
        lines.append(f"- Tags: {', '.join(tags)}")

    category = job.get("category", "other")
    lines.append(f"- Category: {category}")

    scores = job.get("score_breakdown", {})
    if scores:
        score_parts = [f"{k}={v:.2f}" for k, v in scores.items()]
        lines.append(f"- Score breakdown: {', '.join(score_parts)}")

    final_score = job.get("final_score")
    if final_score is not None:
        lines.append(f"- **Final score: {final_score:.3f}**")

    if job.get("verification_status") == "unknown":
        lines.append(f"- ⚠ Verification note: {job.get('verification_reason', '')}")

    desc = job.get("description", "")
    if desc:
        snippet = desc[:200] + "..." if len(desc) > 200 else desc
        lines.append(f"- Description snippet: {snippet}")

    return "\n".join(lines)


def _build_messages(user_query: str, ranked_jobs: list[dict], preferences: dict | None = None) -> list[dict]:
    """构建发送给 LLM 的消息列表。"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_content = f"## User Query\n{user_query}\n\n"

    if preferences:
        user_content += "## Extracted Preferences\n```json\n"
        user_content += json.dumps(preferences, indent=2)
        user_content += "\n```\n\n"

    user_content += f"## Ranked Results ({len(ranked_jobs)} jobs)\n\n"

    if ranked_jobs:
        for i, job in enumerate(ranked_jobs, 1):
            user_content += _format_job_for_prompt(job, i) + "\n\n"
    else:
        user_content += "No matching jobs found.\n"

    messages.append({"role": "user", "content": user_content})
    return messages


def generate_answer(
    user_query: str,
    ranked_jobs: list[dict],
    preferences: dict | None = None,
    api_key: str | None = None,
) -> str:
    """
    核心接口：根据检索结果生成自然语言回答。

    Args:
        user_query: 用户的原始查询
        ranked_jobs: 评分引擎排好序的 top-K 职位列表，每个 dict 应包含：
            - jobs 表全部字段
            - tags: list[str]
            - final_score: float
            - score_breakdown: dict (各维度得分)
        preferences: 查询理解提取的偏好 dict（可选，帮助 LLM 理解匹配逻辑）
        api_key: OpenAI API key

    Returns:
        LLM 生成的自然语言回答字符串
    """
    client = get_client(api_key)

    messages = _build_messages(user_query, ranked_jobs, preferences)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    return response.choices[0].message.content.strip()
