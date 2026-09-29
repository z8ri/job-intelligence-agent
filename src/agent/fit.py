"""Structured fit of a job to salary / location / work-mode conditions.

The legacy `ScoringEngine` already grades these three dimensions (asymmetric salary decay,
tiered metro-area proximity, work-mode adjacency). This module adapts a `Condition` and a
snapshot's scraper `hints` to those functions so the agent and the legacy scorer are one code
path. The result is a grade in [0, 1] plus a short human-readable basis, or None when the
snapshot has nothing to grade with (the caller then falls back to the evidence verdict).

Grades come from scraper guesses, not verified facts: they never exclude a job, they only
order soft preferences and (via `planning`) defer verification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from src.agent.models import Condition, ModesValue, RegionsValue, SalaryValue
from src.agent.snapshots import Snapshot

MIN_PLAUSIBLE_YEARLY_PAY = 10_000  # scrapers also captured hourly/monthly figures; below this is not yearly pay
HOURS_PER_YEAR = 2080
US_WIDE = {"united states", "usa", "us", "u.s.", "america"}
_LOCATION_SPLIT = re.compile(r"\s*(?:•|;|\||\bor\b|/)\s*", re.IGNORECASE)
_STATE_SUFFIX = re.compile(r",\s*[A-Za-z]{2}\b.*$")
_REMOTE_WORDS = re.compile(r"\b(?:fully|100%|hybrid|remote(?:ly)?|anywhere|worldwide|distributed|wfh|work from home)\b", re.IGNORECASE)
_EDGE_PUNCT = " ,-–—:()|/•;\t"


@dataclass(frozen=True)
class Fit:
    score: float
    basis: str


@lru_cache(maxsize=1)
def _engine():
    from src.scoring.engine import ScoringEngine

    return ScoringEngine()


def _yearly(value: SalaryValue) -> float | None:
    if value.min_amount is None or value.currency.upper() != "USD":
        return None
    factor = {"year": 1, "month": 12, "hour": HOURS_PER_YEAR}[value.period]
    return value.min_amount * factor


def salary_fit(value: SalaryValue, hints: dict) -> Fit | None:
    target = _yearly(value)
    lo, hi = hints.get("salary_min") or None, hints.get("salary_max") or None
    known = [x for x in (lo, hi) if x is not None and x >= MIN_PLAUSIBLE_YEARLY_PAY]
    if target is None or not known:
        return None
    job = {"salary_min": min(known), "salary_max": max(known) if len(known) > 1 else None}
    # the condition is a minimum: reaching it is a full fit, only a shortfall is graded (legacy decay)
    score = 1.0 if max(known) >= target else _engine().score_salary(job, target)
    shown = f"{int(min(known)):,}" + (f"-{int(max(known)):,}" if len(known) > 1 else "+")
    return Fit(round(score, 4), f"listed pay {shown} vs target {int(target):,}")


def _location_variants(location: str) -> list[str]:
    parts = [p.strip() for p in _LOCATION_SPLIT.split(location) if p.strip()]
    out: list[str] = []
    for p in parts + [location]:
        out += [p, _STATE_SUFFIX.sub("", p).strip()]
    return [o for o in dict.fromkeys(out) if o]


def region_fit(value: RegionsValue, location: str) -> Fit | None:
    location = (location or "").strip()
    if not location or location.lower() == "unknown":
        return None
    # the legacy scorer rates any "Remote" posting as a near-match for every place; for a stated region
    # that says nothing about where the job is, so only the place words left after removing it are graded
    if _REMOTE_WORDS.search(location):
        stripped = re.sub(r"\s+", " ", _REMOTE_WORDS.sub(" ", location)).strip(_EDGE_PUNCT)
        if not stripped or stripped.lower() in {"or", "and"}:
            return None
        location = re.sub(r"^(?:or|and)\s+|\s+(?:or|and)$", "", stripped, flags=re.I).strip(_EDGE_PUNCT)
    engine = _engine()
    best, basis = 0.0, ""
    for region in value.regions:
        if region.strip().lower() in US_WIDE:
            hit = any(
                v.lower() in US_WIDE or any(v.lower() in {c.lower() for c in info.get("cities", [])} for info in engine.metro_areas.values())
                for v in _location_variants(location)
            )
            score = 1.0 if hit else engine.score_location(location, "united states")
        else:
            score = max(engine.score_location(v, region) for v in _location_variants(location))
        if score > best:
            best, basis = score, f"job location '{location}' vs '{region}'"
    return Fit(round(best, 4), basis)


def mode_fit(value: ModesValue, hints: dict) -> Fit | None:
    job_mode = hints.get("remote")
    matrix = _engine().REMOTE_MATRIX
    if job_mode not in matrix["remote"]:
        return None
    score, mode = max((matrix[m][job_mode], m) for m in value.modes)
    return Fit(round(score, 4), f"job work mode '{job_mode}' vs accepted '{mode}'")


def fit_for(condition: Condition, snapshot: Snapshot | None) -> Fit | None:
    if snapshot is None:
        return None
    v = condition.value
    if isinstance(v, SalaryValue):
        return salary_fit(v, snapshot.hints)
    if isinstance(v, RegionsValue):
        return region_fit(v, snapshot.location)
    if isinstance(v, ModesValue):
        return mode_fit(v, snapshot.hints)
    return None
