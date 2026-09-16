"""Verifier：区分 valid / rejected / unknown，而不是只看排序分数。

排名靠前不等于可以推荐——一个职位可能语义很相关，却是兼职；也可能没有薪资
字段，无法证明满足用户的薪资要求。规则式判断，不调用 LLM（不需要语义理解，
字段/正则判断更快更可控，也不产生额外 API 成本）。

"跨来源同一职位合并"由 src/scoring/fusion.py::fuse_and_rank(dedupe=True) 在
更早的阶段完成，这里不重复处理。
"""

import re

# 保守匹配：只认 part-time/intern/temporary 这类不太会误伤的词，以及括号内
# "(Contract)"/"(Contractor)"/"(1099)" 这类明确标记；"contract"裸词排除紧跟在
# "smart"后面的情况，避免误杀 "Smart Contract Engineer"（区块链全职岗位，
# 和雇佣类型的 contract 是两回事）。数据是 HN 帖子爬的，标题噪声不小，正则
# 规则做不到 100% 准确，这里宁可漏判、不错杀。
#
# 每条规则都要先检查用户原话有没有主动提到同一个词——如果用户本来就是在找
# 实习/合同工/兼职，这条规则不该把它们全拒了（拒得越准，用户越找不到自己
# 要的东西，等于系统性地让这类查询失效）。
_NON_FULLTIME_PATTERNS = {
    "part_time": re.compile(r"\bpart[- ]time\b"),
    "intern": re.compile(r"\bintern(s|ship|ships)?\b"),  # 覆盖复数形式 interns/internships
    "temporary": re.compile(r"\btemporary\b"),
    "temp": re.compile(r"\btemp\b"),
    "contract_1099": re.compile(r"\(1099\)"),
    "contractor_paren": re.compile(r"\(contractor?\)"),
    "contract": re.compile(r"(?<!smart )\bcontract\b"),
}


def _looks_non_fulltime(title: str | None, user_query: str = "") -> bool:
    text = (title or "").lower()
    query = (user_query or "").lower()
    for pattern in _NON_FULLTIME_PATTERNS.values():
        if pattern.search(text) and not pattern.search(query):
            return True
    return False


def verify_jobs(jobs: list[dict], preferences: dict, user_query: str = "") -> list[dict]:
    """给每条职位打 verification_status（valid/rejected/unknown）+ reason。

    原地标注并返回同一个列表：
    - rejected: 标题看起来是兼职/合同工/实习，且用户原话没有主动要求这类职位
    - unknown: 用户提了 target_salary，但该职位完全没有薪资数据，无法验证
    - valid: 其余情况
    """
    target_salary = preferences.get("target_salary")
    for job in jobs:
        if _looks_non_fulltime(job.get("title"), user_query):
            job["verification_status"] = "rejected"
            job["verification_reason"] = "标题包含 part-time/contract/intern 等非全职标记，且用户未主动要求此类职位"
        elif target_salary and not job.get("salary_min") and not job.get("salary_max"):
            job["verification_status"] = "unknown"
            job["verification_reason"] = "用户指定了目标薪资，但该职位未公开薪资范围，无法验证"
        else:
            job["verification_status"] = "valid"
            job["verification_reason"] = ""
    return jobs
