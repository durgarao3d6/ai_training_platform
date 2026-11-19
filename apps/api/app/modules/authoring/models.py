"""AI-assisted authoring tables: ai_job, course_component (open questions section 7).

Rules:
- AI output is stored on ai_job.result as a proposal. Nothing reaches the catalog until a person
  accepts it, and accepted items always start as review_status 'draft'.
- Publishing is a separate admin action; approval is always required.
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import JSON, fk


class AiJobKind(str, enum.Enum):
    draft_course = "draft_course"
    improve_material = "improve_material"
    attach_components = "attach_components"


class AiJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    ready = "ready"  # proposal produced, awaiting human review
    accepted = "accepted"
    dismissed = "dismissed"
    failed = "failed"


class ComponentType(str, enum.Enum):
    resource = "resource"
    reading_note = "reading_note"
    quiz = "quiz"
    starter_file = "starter_file"
    deliverable_manifest = "deliverable_manifest"
    rubric_draft = "rubric_draft"


class AiJob(RecordMixin, Base):
    __tablename__ = "ai_job"

    kind: Mapped[AiJobKind] = mapped_column(Enum(AiJobKind, name="ai_job_kind"), nullable=False)
    status: Mapped[AiJobStatus] = mapped_column(
        Enum(AiJobStatus, name="ai_job_status"), default=AiJobStatus.queued, nullable=False
    )
    requester_id: Mapped[uuid.UUID] = fk("user")
    course_id: Mapped[uuid.UUID | None] = fk("course", nullable=True)
    module_id: Mapped[uuid.UUID | None] = fk("module", nullable=True)
    task_id: Mapped[uuid.UUID | None] = fk("task_template", nullable=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


class CourseMaterial(RecordMixin, Base):
    """A trainer upload. The original file is never modified; accepted edits add a new version."""

    __tablename__ = "course_material"

    module_id: Mapped[uuid.UUID | None] = fk("module", nullable=True)
    task_id: Mapped[uuid.UUID | None] = fk("task_template", nullable=True)
    uploaded_by: Mapped[uuid.UUID] = fk("user")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)


class CourseComponent(RecordMixin, Base):
    __tablename__ = "course_component"

    module_id: Mapped[uuid.UUID | None] = fk("module", nullable=True)
    task_id: Mapped[uuid.UUID | None] = fk("task_template", nullable=True)
    type: Mapped[ComponentType] = mapped_column(
        Enum(ComponentType, name="component_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # draft -> in_review -> approved. Only an admin approves; approved components are shown to interns.
    review_status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", nullable=False
    )
    ai_generated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    ai_job_id: Mapped[uuid.UUID | None] = fk("ai_job", nullable=True)
    created_by: Mapped[uuid.UUID] = fk("user")
    approved_by: Mapped[uuid.UUID | None] = fk("user", nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
