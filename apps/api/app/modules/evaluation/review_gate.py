"""Review gate (Architecture 8.6). Pure function deciding whether a human must review."""

from dataclasses import dataclass
from enum import Enum


class ReviewReason(str, Enum):
    ROLE_ALWAYS_REVIEWS = "role_always_reviews"
    FINAL_DELIVERABLE = "final_deliverable"
    EVIDENCE_UNVERIFIED = "evidence_unverified"
    JUDGE_FLAGGED = "judge_flagged"
    NEAR_THRESHOLD = "near_threshold"
    INJECTION_DETECTED = "injection_detected"
    INTERN_DISAGREES = "intern_disagrees"


@dataclass(frozen=True)
class ReviewFlags:
    role_always_requires_review: bool = False
    is_final_deliverable: bool = False
    evidence_verification_failed: bool = False
    judge_low_confidence: bool = False
    judge_review_flag: bool = False
    injection_detected: bool = False
    intern_disagreed: bool = False


DEFAULT_NEAR_THRESHOLD_MARGIN = 5.0


def needs_review(
    total: float,
    pass_threshold: float,
    flags: ReviewFlags,
    near_threshold_margin: float = DEFAULT_NEAR_THRESHOLD_MARGIN,
) -> list[ReviewReason]:
    """Return every reason a human must review. An empty list means none is required."""
    reasons: list[ReviewReason] = []
    if flags.role_always_requires_review:
        reasons.append(ReviewReason.ROLE_ALWAYS_REVIEWS)
    if flags.is_final_deliverable:
        reasons.append(ReviewReason.FINAL_DELIVERABLE)
    if flags.evidence_verification_failed:
        reasons.append(ReviewReason.EVIDENCE_UNVERIFIED)
    if flags.judge_low_confidence or flags.judge_review_flag:
        reasons.append(ReviewReason.JUDGE_FLAGGED)
    if abs(total - pass_threshold) <= near_threshold_margin:
        reasons.append(ReviewReason.NEAR_THRESHOLD)
    if flags.injection_detected:
        reasons.append(ReviewReason.INJECTION_DETECTED)
    if flags.intern_disagreed:
        reasons.append(ReviewReason.INTERN_DISAGREES)
    return reasons
