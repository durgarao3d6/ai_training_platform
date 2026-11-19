"""Evaluation tables: evaluation_run, stage_result, criterion_score, finding, correction_task."""

import enum
import uuid
from typing import Any

from sqlalchemy import Boolean, Enum, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import JSON, fk


class RunState(str, enum.Enum):
    """Architecture 8.1."""

    submitted = "SUBMITTED"
    validated = "VALIDATED"
    completeness_checked = "COMPLETENESS_CHECKED"
    autochecked = "AUTOCHECKED"
    ai_rubric = "AI_RUBRIC"
    scored = "SCORED"
    feedback = "FEEDBACK"
    correction_created = "CORRECTION_CREATED"
    human_review = "HUMAN_REVIEW"
    approved = "APPROVED"
    revision_required = "REVISION_REQUIRED"
    error_retrying = "ERROR_RETRYING"
    needs_human = "NEEDS_HUMAN"


class FindingSource(str, enum.Enum):
    tool = "tool"
    ai = "ai"
    trainer = "trainer"


class Severity(str, enum.Enum):
    info = "info"
    warning = "warning"
    blocking = "blocking"


class EvaluationRun(RecordMixin, Base):
    """Pins rubric version, prompt version, model id and tool versions for reproducibility."""

    __tablename__ = "evaluation_run"

    submission_id: Mapped[uuid.UUID] = fk("submission")
    rubric_version_id: Mapped[uuid.UUID] = fk("rubric_version")
    # Store the spec's uppercase values (SUBMITTED, ...) rather than the member names.
    state: Mapped[RunState] = mapped_column(
        Enum(RunState, name="run_state", values_callable=lambda e: [m.value for m in e]),
        default=RunState.submitted,
        nullable=False,
    )
    prompt_versions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(100))
    tool_versions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    runner_image_versions: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    total_score: Mapped[float | None] = mapped_column(Float)
    outcome: Mapped[str | None] = mapped_column(String(30))  # PASS_CANDIDATE | REVISION_REQUIRED
    review_reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


class StageResult(RecordMixin, Base):
    """Idempotent per (run, stage, input_hash)."""

    __tablename__ = "stage_result"
    __table_args__ = (
        UniqueConstraint("run_id", "stage", "input_hash", name="uq_stage_result_run_stage_input"),
    )

    run_id: Mapped[uuid.UUID] = fk("evaluation_run")
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # started | completed | failed


class CriterionScore(RecordMixin, Base):
    __tablename__ = "criterion_score"
    __table_args__ = (
        UniqueConstraint("run_id", "criterion_id", name="uq_criterion_score_run_criterion"),
    )

    run_id: Mapped[uuid.UUID] = fk("evaluation_run")
    criterion_id: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_rating: Mapped[int | None] = mapped_column(Integer)
    final_rating: Mapped[int] = mapped_column(Integer, nullable=False)  # after rating caps
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Finding(RecordMixin, Base):
    __tablename__ = "finding"

    run_id: Mapped[uuid.UUID] = fk("evaluation_run")
    source: Mapped[FindingSource] = mapped_column(
        Enum(FindingSource, name="finding_source"), nullable=False
    )
    checker_key: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"), nullable=False)
    criterion_id: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rating_cap: Mapped[int | None] = mapped_column(Integer)


class CorrectionTask(RecordMixin, Base):
    __tablename__ = "correction_task"

    run_id: Mapped[uuid.UUID] = fk("evaluation_run")
    criterion_id: Mapped[str] = mapped_column(String(100), nullable=False)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False
    )  # open | resolved
