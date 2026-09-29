"""Condition schema: what the user asked for, with verbatim provenance and versioning.

Every condition carries the exact words of the user's request it came from
(`quote`), a hard/soft flag, and a typed value. "Remote" (how the job is worked)
and "work_region" (where the user can legally/physically work) are separate
fields, and salary keeps currency, period, base-vs-total and region, so later
evidence checks never have to guess what a bare number meant.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

ConditionField = Literal[
    "role_focus",       # work the user wants to do
    "role_avoid",       # work the user does not want to be the main content
    "skill",
    "seniority",
    "employment_type",
    "work_region",      # where the user can work (checked against allowed regions)
    "remote_mode",      # remote / hybrid / onsite acceptance
    "salary",
    "other",
]
Strength = Literal["hard", "soft"]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


class TextValue(BaseModel):
    kind: Literal["text"] = "text"
    text: str = Field(min_length=1)

    def canonical(self) -> dict:
        return {"text": _norm(self.text)}


class SalaryValue(BaseModel):
    kind: Literal["salary"] = "salary"
    currency: str = "USD"
    period: Literal["year", "month", "hour"] = "year"
    basis: Literal["base", "total", "unspecified"] = "unspecified"
    min_amount: float | None = None
    region: str | None = None

    def canonical(self) -> dict:
        return {
            "currency": self.currency.upper(),
            "period": self.period,
            "basis": self.basis,
            "min_amount": self.min_amount,
            "region": _norm(self.region) if self.region else None,
        }


class RegionsValue(BaseModel):
    kind: Literal["regions"] = "regions"
    regions: list[str] = Field(min_length=1)

    def canonical(self) -> dict:
        return {"regions": sorted(_norm(r) for r in self.regions)}


class ModesValue(BaseModel):
    kind: Literal["modes"] = "modes"
    modes: list[Literal["remote", "hybrid", "onsite"]] = Field(min_length=1)

    def canonical(self) -> dict:
        return {"modes": sorted(set(self.modes))}


class EmploymentValue(BaseModel):
    kind: Literal["employment"] = "employment"
    types: list[Literal["full_time", "part_time", "internship", "contract"]] = Field(min_length=1)

    def canonical(self) -> dict:
        return {"types": sorted(set(self.types))}


class ExperienceValue(BaseModel):
    kind: Literal["experience"] = "experience"
    level: Literal["intern", "entry", "junior", "mid", "senior", "staff"] | None = None
    max_years_required: int | None = None

    def canonical(self) -> dict:
        return {"level": self.level, "max_years_required": self.max_years_required}


Value = Annotated[
    Union[TextValue, SalaryValue, RegionsValue, ModesValue, EmploymentValue, ExperienceValue],
    Field(discriminator="kind"),
]

DEFAULT_SOFT_WEIGHT = 0.5

_FIELD_KIND: dict[str, str] = {
    "role_focus": "text",
    "role_avoid": "text",
    "skill": "text",
    "other": "text",
    "seniority": "experience",
    "employment_type": "employment",
    "work_region": "regions",
    "remote_mode": "modes",
    "salary": "salary",
}


class Condition(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: ConditionField
    strength: Strength
    value: Value
    quote: str = Field(min_length=1)
    weight: float | None = Field(default=None, ge=0.05, le=1.0)  # emphasis of a soft condition; None = default

    @property
    def effective_weight(self) -> float:
        """Hard conditions filter (weight 1); soft ones default to 0.5 unless the user stressed them."""
        if self.strength == "hard":
            return 1.0
        return self.weight if self.weight is not None else DEFAULT_SOFT_WEIGHT

    @model_validator(mode="after")
    def _kind_matches_field(self):
        expected = _FIELD_KIND[self.field]
        if self.value.kind != expected:
            raise ValueError(f"field '{self.field}' needs a '{expected}' value, got '{self.value.kind}'")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """Stable across versions: derived from field + normalized value only, so
        flipping hard/soft or rewording the quote keeps the same id."""
        payload = json.dumps([self.field, self.value.canonical()], sort_keys=True)
        return f"{self.field}:{hashlib.sha1(payload.encode()).hexdigest()[:8]}"

    def signature(self) -> str:
        """Identity plus strength: what a cached judgement actually depends on."""
        return f"{self.id}:{self.strength}"


class Clarification(BaseModel):
    """A question worth asking only because the answer would change which jobs qualify."""

    question: str = Field(min_length=1)
    reason: str = ""
    options: list[str] = Field(default_factory=list)
    affects: list[ConditionField] = Field(default_factory=list)


class ConditionChanges(BaseModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)  # same id, different strength or weight

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.modified)

    @property
    def changed_ids(self) -> set[str]:
        return set(self.added) | set(self.removed) | set(self.modified)


class ConditionSet(BaseModel):
    raw_query: str
    version: int = 1
    conditions: list[Condition]
    clarifications: list[Clarification] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self):
        haystack = _norm(self.raw_query)
        seen: set[str] = set()
        for c in self.conditions:
            if _norm(c.quote) not in haystack:
                raise ValueError(f"quote {c.quote!r} is not a verbatim part of the query")
            if c.id in seen:
                raise ValueError(f"duplicate condition {c.id}")
            seen.add(c.id)
        return self

    def hard(self) -> list[Condition]:
        return [c for c in self.conditions if c.strength == "hard"]

    def soft(self) -> list[Condition]:
        return [c for c in self.conditions if c.strength == "soft"]

    def get(self, condition_id: str) -> Condition | None:
        return next((c for c in self.conditions if c.id == condition_id), None)

    def retrieval_text(self) -> str:
        """Text used to retrieve by work content. Location, salary, employment
        and 'avoid' conditions are excluded: they are checked later against
        evidence, and 'avoid' text would pull in exactly the wrong jobs."""
        parts = [
            c.value.text  # type: ignore[union-attr]
            for c in self.conditions
            if c.field in ("role_focus", "skill")
        ]
        return " ; ".join(parts) if parts else self.raw_query

    def fingerprint(self) -> str:
        sigs = sorted(f"{c.signature()}:{c.effective_weight}" for c in self.conditions)
        return hashlib.sha1(json.dumps(sigs).encode()).hexdigest()[:12]

    def revise(
        self,
        raw_query: str,
        conditions: list[Condition],
        clarifications: list[Clarification] | None = None,
    ) -> tuple["ConditionSet", ConditionChanges]:
        """Return the next version. The version only advances when a condition was
        added, removed or changed strength/weight; rewording alone keeps it, so cached
        judgements stay valid."""
        old = {c.id: c for c in self.conditions}
        new = {c.id: c for c in conditions}
        changes = ConditionChanges(
            added=sorted(set(new) - set(old)),
            removed=sorted(set(old) - set(new)),
            modified=sorted(
                i for i in set(old) & set(new)
                if old[i].strength != new[i].strength or old[i].effective_weight != new[i].effective_weight
            ),
        )
        version = self.version if changes.is_empty else self.version + 1
        revised = ConditionSet(
            raw_query=raw_query,
            version=version,
            conditions=conditions,
            clarifications=clarifications or [],
        )
        return revised, changes
