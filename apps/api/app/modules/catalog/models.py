"""Catalog tables: role_profile, course, module, task_template, rubric_version (Architecture 6.1)."""

import enum
import uuid
from typing import Any

from sqlalchemy import Boolean, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import JSON, fk

# module.created_by references "user": register that table whenever the catalog is loaded, so
# entry points that import only the catalog (content import, seed) can still flush modules.
from app.modules.identity import models as _identity  # noqa: F401


class TaskType(str, enum.Enum):
    practical = "practical"
    integration = "integration"
    assessment = "assessment"


class TaskDepth(str, enum.Enum):
    demo = "demo"
    content = "content"


class RoleProfile(RecordMixin, Base):
    __tablename__ = "role_profile"

    key: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )  # developer, ba, qa, uiux
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    checker_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    judge_prompt_key: Mapped[str | None] = mapped_column(String(100))
    review_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Course(RecordMixin, Base):
    __tablename__ = "course"

    role_profile_id: Mapped[uuid.UUID] = fk("role_profile")
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # draft until the track's role expert approves it for real interns.
    review_status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", nullable=False
    )
    final_deliverable: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Module(RecordMixin, Base):
    """A milestone within a course."""

    __tablename__ = "module"
    __table_args__ = (UniqueConstraint("course_id", "position", name="uq_module_course_position"),)

    course_id: Mapped[uuid.UUID] = fk("course")
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    learning_objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # draft modules (trainer or AI created) are invisible to interns until an admin approves them.
    # Existing rows are approved. Only approved modules sync to enrollments.
    review_status: Mapped[str] = mapped_column(
        String(20), default="approved", server_default="approved", nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = fk("user", nullable=True)


class RubricVersion(RecordMixin, Base):
    """Immutable once published; identified by content hash. A DB trigger enforces immutability."""

    __tablename__ = "rubric_version"

    rubric_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    published: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    __table_args__ = (
        UniqueConstraint("rubric_key", "version", name="uq_rubric_version_key_version"),
    )


class TaskTemplate(RecordMixin, Base):
    __tablename__ = "task_template"

    module_id: Mapped[uuid.UUID] = fk("module")
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType, name="task_type"), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    learning_objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    deliverables: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    depth: Mapped[TaskDepth] = mapped_column(Enum(TaskDepth, name="task_depth"), nullable=False)
    rubric_version_id: Mapped[uuid.UUID | None] = fk("rubric_version", nullable=True)
    # Plain-language summaries, used where no published rubric exists yet (content-only tasks).
    submits: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evaluated_on: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Review rule: every UX task and each track's final milestone (Milestone Catalog section 1).
    requires_review: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    starter_files: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
