"""Verifier: distinguish valid / rejected / unknown instead of relying on ranking score alone.

Ranking high does not mean a job can be recommended: a posting may be
semantically relevant yet part-time, or lack a salary field so it cannot be
shown to meet the user's salary requirement. This is rule-based and does not
call the LLM (no semantic understanding is needed; field/regex checks are faster,
more controllable, and incur no extra API cost).

Merging the same posting across sources is handled earlier by
src/scoring/fusion.py::fuse_and_rank(dedupe=True) and is not repeated here.
"""

import re

# Conservative matching: only recognize words unlikely to cause false positives,
# such as part-time/intern/temporary, plus explicit parenthesized markers like
# "(Contract)"/"(Contractor)"/"(1099)". The bare word "contract" excludes the
# case where it directly follows "smart", so "Smart Contract Engineer" (a
# full-time blockchain role, unrelated to contract employment) is not killed.
# The data is scraped from HN posts and titles are noisy; regex rules cannot be
# 100% accurate, so prefer missing a case over rejecting a good job.
#
# Every rule first checks whether the user's own query mentions the same word.
# If the user is explicitly looking for internships/contract/part-time work,
# the rule must not reject them all (the more precisely it rejects, the less the
# user can find what they asked for, which would systematically break such queries).
_NON_FULLTIME_PATTERNS = {
    "part_time": re.compile(r"\bpart[- ]time\b"),
    "intern": re.compile(r"\bintern(s|ship|ships)?\b"),  # also covers the plural forms interns/internships
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
    """Assign each job a verification_status (valid/rejected/unknown) plus a reason.

    Annotates in place and returns the same list:
    - rejected: the title looks part-time/contract/intern and the user's query did not ask for such roles
    - unknown: the user gave a target_salary but the job has no salary data at all, so it cannot be verified
    - valid: everything else
    """
    target_salary = preferences.get("target_salary")
    for job in jobs:
        if _looks_non_fulltime(job.get("title"), user_query):
            job["verification_status"] = "rejected"
            job["verification_reason"] = "Title contains a non-full-time marker (part-time/contract/intern) and the user did not ask for such roles"
        elif target_salary and not job.get("salary_min") and not job.get("salary_max"):
            job["verification_status"] = "unknown"
            job["verification_reason"] = "User specified a target salary but this posting discloses no salary range; cannot verify"
        else:
            job["verification_status"] = "valid"
            job["verification_reason"] = ""
    return jobs
