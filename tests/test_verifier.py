"""Unit tests for src/scoring/verifier.py. Pure rule-based function, no mocking needed."""

from src.scoring.verifier import verify_jobs


def _job(job_id="j1", title="Backend Engineer", salary_min=None, salary_max=None):
    return {"job_id": job_id, "title": title, "salary_min": salary_min, "salary_max": salary_max}


class TestVerifyJobs:
    def test_fulltime_role_with_salary_is_valid(self):
        jobs = [_job(title="Senior Backend Engineer", salary_min=150000, salary_max=180000)]
        out = verify_jobs(jobs, preferences={"target_salary": 150000})
        assert out[0]["verification_status"] == "valid"

    def test_internship_title_rejected_when_user_did_not_ask_for_it(self):
        jobs = [_job(title="Software Engineering Intern")]
        out = verify_jobs(jobs, preferences={}, user_query="senior backend engineer")
        assert out[0]["verification_status"] == "rejected"

    def test_internship_title_kept_when_user_explicitly_wants_internship(self):
        jobs = [_job(title="Software Engineering Intern")]
        out = verify_jobs(jobs, preferences={}, user_query="software engineering internship for undergrads")
        assert out[0]["verification_status"] == "valid"

    def test_plural_internship_forms_are_caught(self):
        # Regression: \bintern(ship)?\b originally missed "Interns"/"Internships".
        for title in ["ML Interns Wanted", "Backend Internships Program"]:
            out = verify_jobs([_job(title=title)], preferences={}, user_query="python jobs")
            assert out[0]["verification_status"] == "rejected", title

    def test_smart_contract_engineer_is_not_treated_as_a_contract_role(self):
        jobs = [_job(title="Smart Contract Engineer")]
        out = verify_jobs(jobs, preferences={}, user_query="blockchain jobs")
        assert out[0]["verification_status"] == "valid"

    def test_bare_contract_title_rejected(self):
        jobs = [_job(title="Backend Engineer (Contract)")]
        out = verify_jobs(jobs, preferences={}, user_query="backend engineer")
        assert out[0]["verification_status"] == "rejected"

    def test_missing_salary_with_target_is_unknown_not_rejected(self):
        jobs = [_job(title="Backend Engineer", salary_min=None, salary_max=None)]
        out = verify_jobs(jobs, preferences={"target_salary": 150000})
        assert out[0]["verification_status"] == "unknown"

    def test_missing_salary_without_target_is_valid(self):
        jobs = [_job(title="Backend Engineer", salary_min=None, salary_max=None)]
        out = verify_jobs(jobs, preferences={"target_salary": None})
        assert out[0]["verification_status"] == "valid"

    def test_annotates_in_place_and_returns_same_length(self):
        jobs = [_job(job_id="j1"), _job(job_id="j2", title="Backend Intern")]
        out = verify_jobs(jobs, preferences={}, user_query="python jobs")
        assert len(out) == 2
        assert out is jobs  # in-place annotation, not a filtered copy
