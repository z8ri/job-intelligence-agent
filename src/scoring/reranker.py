"""LLM 精排：对粗分 Top-N 候选做更细致的 query-职位相关性判断。

BM25/TF-IDF 看词面重合、Dense 看整体语义相似度，都不是真正联合看"这条 query
具体在问什么、这条职位具体是不是在满足它"。这里用 GPT-4o-mini 对 Top-N 候选
的标题+摘要和 query 一起打分（LLM+Schema 风格，结构化输出，不是让 LLM 直接
决定推荐结果），替换掉粗分里不够精细的部分。
"""

import json

from src.llm import MODEL, get_client

RERANK_TOP_N = 50
# 很多职位描述开头是公司介绍套话（"XX is growing our team of..."），真正的
# 职责/技能要求经常要到几百字之后才出现；300 字符截断实测会把摘要截在套话
# 里，LLM 看不到任何实质信息导致相关性打分失真。1200 字符能覆盖大多数职位
# 的实质内容，API 成本仍可忽略（50 条候选约 15k tokens，一次调用几分之一美分）。
_MAX_DESC_CHARS = 1200

SYSTEM_PROMPT = """You are a job search relevance judge. Given a user query and \
a list of job postings (id, title, short description), score how well each \
job matches the query's intent on a 0.0-1.0 scale (1.0 = perfectly relevant, \
0.0 = unrelated). Judge relevance only — ignore salary/location/remote, those \
are scored separately downstream.
Output ONLY a JSON object mapping job id -> score, e.g. {"hn_123": 0.85, ...}.
No explanation, no markdown."""


def rerank(
    query: str,
    candidates: list[dict],
    top_n: int = RERANK_TOP_N,
    api_key: str | None = None,
) -> dict[str, float]:
    """对 candidates 的前 top_n 条做 LLM 精排，返回 {job_id: score}。

    candidates 应已按粗分数降序排列（调用方负责排序）。任何失败（网络、JSON
    解析、格式不对）整体降级返回 {}——调用方据此跳过覆盖，原有粗分排序原样
    保留，不重试、不中断 pipeline（重排是锦上添花，不是关键路径）。
    """
    subset = candidates[:top_n]
    if not subset:
        return {}

    listing = [
        {
            "id": c["job_id"],
            "title": c.get("title") or "",
            "summary": (c.get("description") or "")[:_MAX_DESC_CHARS],
        }
        for c in subset
    ]
    valid_ids = {c["job_id"] for c in subset}

    try:
        client = get_client(api_key)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Query: {query}\n\nJobs:\n{json.dumps(listing)}"},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    scores: dict[str, float] = {}
    for jid, val in data.items():
        if jid not in valid_ids:
            continue  # 忽略 LLM 编造的、不在候选里的 id
        try:
            scores[jid] = max(0.0, min(1.0, float(val)))
        except (TypeError, ValueError):
            continue
    return scores
