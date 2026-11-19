"""Submissions tables: submission, artifact."""

import enum
import uuid

from sqlalchemy import BigInteger, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import fk


class SubmissionStatus(str, enum.Enum):
    received = "received"
    evaluating = "evaluating"
    evaluated = "evaluated"
    rejected = "rejected"  # failed validation


class ArtifactKind(str, enum.Enum):
    file = "file"
    link = "link"
    text = "text"


class Submission(RecordMixin, Base):
    """One attempt. Earlier attempts are never updated."""

    __tablename__ = "submission"
    __table_args__ = (
        UniqueConstraint(
            "task_instance_id", "attempt_number", name="uq_submission_task_instance_attempt"
        ),
        UniqueConstraint(
            "task_instance_id", "idempotency_key", name="uq_submission_task_instance_idem"
        ),
    )

    task_instance_id: Mapped[uuid.UUID] = fk("task_instance")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"),
        default=SubmissionStatus.received,
        nullable=False,
    )


class Artifact(RecordMixin, Base):
    __tablename__ = "artifact"

    submission_id: Mapped[uuid.UUID] = fk("submission")
    deliverable_id: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[ArtifactKind] = mapped_column(
        Enum(ArtifactKind, name="artifact_kind"), nullable=False
    )
    content_type: Mapped[str | None] = mapped_column(String(200))
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    filename: Mapped[str | None] = mapped_column(String(255))  # original name, kind = file
    url: Mapped[str | None] = mapped_column(String(2000))  # kind = link
    text_content: Mapped[str | None] = mapped_column(Text)  # kind = text
