"""Delivery tables: cohort, enrollment, task_instance (Architecture 6.2)."""

import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import fk


class TaskInstanceStatus(str, enum.Enum):
    locked = "locked"
    unlocked = "unlocked"
    in_progress = "in_progress"
    needs_another_pass = "needs_another_pass"
    review_pending = "review_pending"
    complete = "complete"


class Cohort(RecordMixin, Base):
    __tablename__ = "cohort"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_on: Mapped[date | None] = mapped_column(Date)
    trainer_id: Mapped[uuid.UUID | None] = fk("user", nullable=True)


class Enrollment(RecordMixin, Base):
    __tablename__ = "enrollment"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),)

    user_id: Mapped[uuid.UUID] = fk("user")
    cohort_id: Mapped[uuid.UUID] = fk("cohort")
    course_id: Mapped[uuid.UUID] = fk("course")


class TaskInstance(RecordMixin, Base):
    __tablename__ = "task_instance"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "task_template_id", name="uq_task_instance_enrollment_task"
        ),
    )

    enrollment_id: Mapped[uuid.UUID] = fk("enrollment")
    task_template_id: Mapped[uuid.UUID] = fk("task_template")
    status: Mapped[TaskInstanceStatus] = mapped_column(
        Enum(TaskInstanceStatus, name="task_instance_status"),
        default=TaskInstanceStatus.locked,
        nullable=False,
    )
