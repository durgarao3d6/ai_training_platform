"""Review tables: review_decision, intervention, message."""

import enum
import uuid

from sqlalchemy import Boolean, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import fk


class Decision(str, enum.Enum):
    approve = "approve"
    request_revision = "request_revision"
    override = "override"


class ReviewDecision(RecordMixin, Base):
    __tablename__ = "review_decision"

    run_id: Mapped[uuid.UUID] = fk("evaluation_run")
    reviewer_id: Mapped[uuid.UUID] = fk("user")
    decision: Mapped[Decision] = mapped_column(Enum(Decision, name="decision"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)  # required for override (enforced in service)


class Intervention(RecordMixin, Base):
    __tablename__ = "intervention"

    task_instance_id: Mapped[uuid.UUID] = fk("task_instance")
    trainer_id: Mapped[uuid.UUID] = fk("user")
    note: Mapped[str] = mapped_column(Text, nullable=False)


class Message(RecordMixin, Base):
    __tablename__ = "message"

    task_instance_id: Mapped[uuid.UUID] = fk("task_instance")
    sender_id: Mapped[uuid.UUID] = fk("user")
    recipient_id: Mapped[uuid.UUID | None] = fk("user", nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_disagreement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
