"""Unit tests for src/scoring/engine.py — covers 4 atomic scoring functions
(salary, location, tags, remote). Composite compute_final_score is verified
by §7.7 ablation, not here.
"""
import math
import pytest

from src.scoring.engine import ScoringEngine


TOL = 0.01


@pytest.fixture(scope="module")
def engine():
    return ScoringEngine()


# ---------- 1. Salary asymmetric Gaussian ----------

class TestScoreSalary:
    @pytest.mark.parametrize("job, target, expected", [
        # 1. No target → 1.0 (no preference)
        ({"salary_min": 100000, "salary_max": 100000}, None, 1.0),
        # 2. No salary in job → 0.5 (neutral fallback)
        ({"salary_min": None, "salary_max": None}, 100000, 0.5),
        # 3. Target inside [min, max] → effective clamped to target → 1.0
        ({"salary_min": 80000, "salary_max": 120000}, 100000, 1.0),
        # 4. Slightly below target → near 1.0 (σ_low=20000)
        #    delta=-1000, sigma=20000 → exp(-(1/20)^2) = exp(-0.0025) ≈ 0.9975
        ({"salary_min": 99000, "salary_max": 99000}, 100000, math.exp(-0.0025)),
        # 5. Far above target → exp(-4) ≈ 0.0183 (σ_high=50000)
        ({"salary_min": 200000, "salary_max": 200000}, 100000, math.exp(-4)),
        # 6. Far below target → exp(-6.25) ≈ 0.00193 (σ_low=20000, harsher)
        ({"salary_min": 50000, "salary_max": 50000}, 100000, math.exp(-6.25)),
        # 7. Single bound (max only) → uses max as effective
        #    delta=20000, sigma=50000 → exp(-0.16) ≈ 0.852
        ({"salary_min": None, "salary_max": 120000}, 100000, math.exp(-0.16)),
        # 8. target=0 is falsy → treated as no preference → 1.0
        ({"salary_min": 100000, "salary_max": 100000}, 0, 1.0),
    ])
    def test_salary(self, engine, job, target, expected):
        actual = engine.score_salary(job, target)
        assert abs(actual - expected) < TOL


# ---------- 2. Location hierarchical ----------

class TestScoreLocation:
    @pytest.mark.parametrize("job_loc, pref_loc, expected", [
        # 1. No preference → 1.0
        ("New York", None, 1.0),
        # 2. Job location Unknown → 0.3
        ("Unknown", "New York", 0.3),
        # 3. US-flavored remote (contains 'us' / 'usa') → 0.85
        ("Remote (US only)", "New York", 0.85),
        # 4. Exact match → 1.0
        ("San Francisco", "San Francisco", 1.0),
        # 5. Same metro (SF cluster) → 1.0 (alias resolves to exact match)
        ("Oakland", "San Francisco", 1.0),
        # 6. Same metro (different city pair within SF) → 1.0
        ("Berkeley", "Palo Alto", 1.0),
        # 7. State match (job=state code, pref in metro) → 0.5
        ("ca", "San Francisco", 0.5),
        # 8. Different metro, no overlap → 0.1
        ("Tokyo", "New York", 0.1),
        # 9. Case insensitive → 1.0
        ("SAN FRANCISCO", "san francisco", 1.0),
        # 10. Empty pref string → 1.0 (falsy)
        ("New York", "", 1.0),
        # 11. Pure Remote → 0.9 (no geographic conflict)
        ("Remote", "New York", 0.9),
        # 12. Foreign remote → 0.4
        ("Brazil - Remote", "New York City", 0.4),
        # 13. Same metro + remote → 0.85
        ("Brooklyn - Remote", "New York City", 0.85),
        # 14. NYC alias hit (nyc → new york metro)
        ("Manhattan", "nyc", 1.0),
        # 15. State full name "Texas" → in-state city → 1.0 (state-level pref)
        ("Austin, TX", "Texas", 1.0),
        # 16. State pref "Texas" + in-state metro city (no state code) → 1.0
        ("dallas", "Texas", 1.0),
        # 17. State pref "Texas" + neighbor-state city → 0.5
        ("New Orleans, LA", "Texas", 0.5),
        # 18. State pref "Texas" + non-neighbor city → 0.1
        ("Boston, MA", "Texas", 0.1),
        # 19. State pref "Texas" + pure remote → 0.85 (US scope likely covers TX)
        ("Remote", "Texas", 0.85),
        # 20. State pref "Texas" + US remote → 0.85
        ("Remote (US only)", "Texas", 0.85),
        # 21. State pref "Texas" + foreign remote → 0.4
        ("Brazil - Remote", "Texas", 0.4),
        # 22. State pref "California" + SF → 1.0
        ("San Francisco", "California", 1.0),
    ])
    def test_location(self, engine, job_loc, pref_loc, expected):
        actual = engine.score_location(job_loc, pref_loc)
        assert abs(actual - expected) < TOL


# ---------- 3. Tags modified Jaccard ----------

class TestScoreTags:
    @pytest.mark.parametrize("job_tags, desired_tags, expected", [
        # 1. No desired → 1.0 (no preference)
        (["python"], [], 1.0),
        # 2. Empty job tags → 0.0
        ([], ["python"], 0.0),
        # 3. Job has extras → still 1.0 (job extras NOT penalized — key property of modified Jaccard)
        (["python", "react", "aws"], ["python", "react"], 1.0),
        # 4. Partial match: hits=1, desired=3 → 1/3
        (["python"], ["python", "react", "aws"], 1 / 3),
        # 5. No overlap → 0.0
        (["java"], ["python"], 0.0),
        # 6. Case insensitive single → 1.0
        (["python"], ["Python"], 1.0),
        # 7. Case insensitive multi → 1.0
        (["PYTHON", "React"], ["python", "react"], 1.0),
    ])
    def test_tags(self, engine, job_tags, desired_tags, expected):
        actual = engine.score_tags(job_tags, desired_tags)
        assert abs(actual - expected) < TOL


# ---------- 4. Remote 4×5 matrix ----------

class TestScoreRemote:
    # 20 matrix cells: 4 prefs × 5 job_remote values
    @pytest.mark.parametrize("pref, job, expected", [
        # pref=remote
        ("remote", "remote", 1.0),
        ("remote", "hybrid", 0.4),
        ("remote", "onsite", 0.1),
        ("remote", "unknown", 0.3),
        ("remote", "remote_or_onsite", 1.0),
        # pref=hybrid
        ("hybrid", "remote", 0.6),
        ("hybrid", "hybrid", 1.0),
        ("hybrid", "onsite", 0.5),
        ("hybrid", "unknown", 0.4),
        ("hybrid", "remote_or_onsite", 0.8),
        # pref=onsite
        ("onsite", "remote", 0.2),
        ("onsite", "hybrid", 0.6),
        ("onsite", "onsite", 1.0),
        ("onsite", "unknown", 0.4),
        ("onsite", "remote_or_onsite", 1.0),
        # pref=remote_or_onsite
        ("remote_or_onsite", "remote", 1.0),
        ("remote_or_onsite", "hybrid", 0.8),
        ("remote_or_onsite", "onsite", 1.0),
        ("remote_or_onsite", "unknown", 0.5),
        ("remote_or_onsite", "remote_or_onsite", 1.0),
    ])
    def test_remote_matrix(self, engine, pref, job, expected):
        actual = engine.score_remote(job, pref)
        assert abs(actual - expected) < TOL

    # 2 edge cases
    @pytest.mark.parametrize("pref, job, expected", [
        # No preference → 1.0
        (None, "remote", 1.0),
        # Unmapped job_remote value → 0.3 fallback
        ("remote", "invalid_value", 0.3),
    ])
    def test_remote_edge(self, engine, pref, job, expected):
        actual = engine.score_remote(job, pref)
        assert abs(actual - expected) < TOL
