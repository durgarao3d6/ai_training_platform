"""Scoring service (Architecture 8.5). Pure function: no I/O, no LLM, no clock.

The LLM supplies per-criterion ratings. This module applies tool-derived rating caps,
weights, mandatory gates and the pass threshold. Scores are never set by the LLM.
Covers FR-EVAL scoring requirements.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

MIN_RATING = 0
MAX_RATING = 4


class Outcome(str, Enum):
    PASS_CANDIDATE = "PASS_CANDIDATE"
    REVISION_REQUIRED = "REVISION_REQUIRED"


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    blocking = "blocking"


@dataclass(frozen=True)
class CriterionSpec:
    id: str
    weight: int
    mandatory_min_level: int | None = None


@dataclass(frozen=True)
class FindingInput:
    severity: Severity
    criterion_id: str | None = None
    rating_cap: int | None = None


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: str
    llm_rating: int
    final_rating: int
    weight: int
    points: float
    capped: bool


@dataclass(frozen=True)
class GateFailure:
    reason: str  # "mandatory_min_level" | "blocking_finding"
    criterion_id: str | None = None


@dataclass(frozen=True)
class ScoreResult:
    total: float
    criteria: tuple[CriterionResult, ...]
    gate_failures: tuple[GateFailure, ...]
    outcome: Outcome


class ScoringError(ValueError):
    """Inputs are inconsistent (the caller must fix them; we never guess)."""


def _check_rating(value: int, label: str) -> None:
    if not MIN_RATING <= value <= MAX_RATING:
        raise ScoringError(f"{label} must be between {MIN_RATING} and {MAX_RATING}, got {value}")


def score(
    criteria: Sequence[CriterionSpec],
    llm_ratings: Mapping[str, int],
    findings: Sequence[FindingInput],
    pass_threshold: float,
) -> ScoreResult:
    ids = [c.id for c in criteria]
    if len(set(ids)) != len(ids):
        raise ScoringError("duplicate criterion ids")
    if sum(c.weight for c in criteria) != 100:
        raise ScoringError("criterion weights must sum to 100")
    unknown = set(llm_ratings) - set(ids)
    if unknown:
        raise ScoringError(f"ratings for unknown criteria: {sorted(unknown)}")
    missing = set(ids) - set(llm_ratings)
    if missing:
        raise ScoringError(f"missing ratings for criteria: {sorted(missing)}")

    results: list[CriterionResult] = []
    failures: list[GateFailure] = []

    for spec in criteria:
        llm_rating = llm_ratings[spec.id]
        _check_rating(llm_rating, f"rating for {spec.id}")
        caps = [
            f.rating_cap for f in findings if f.criterion_id == spec.id and f.rating_cap is not None
        ]
        for cap in caps:
            _check_rating(cap, f"rating cap for {spec.id}")
        final = min([llm_rating, *caps])
        results.append(
            CriterionResult(
                criterion_id=spec.id,
                llm_rating=llm_rating,
                final_rating=final,
                weight=spec.weight,
                points=spec.weight * final / MAX_RATING,
                capped=final < llm_rating,
            )
        )
        if spec.mandatory_min_level is not None and final < spec.mandatory_min_level:
            failures.append(GateFailure("mandatory_min_level", spec.id))

    for finding in findings:
        if finding.severity is Severity.blocking:
            failures.append(GateFailure("blocking_finding", finding.criterion_id))

    total = sum(r.points for r in results)
    passed = total >= pass_threshold and not failures
    return ScoreResult(
        total=total,
        criteria=tuple(results),
        gate_failures=tuple(failures),
        outcome=Outcome.PASS_CANDIDATE if passed else Outcome.REVISION_REQUIRED,
    )
