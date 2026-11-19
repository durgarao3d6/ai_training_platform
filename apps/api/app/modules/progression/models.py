"""Progression tables: milestone_progress."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import fk


class MilestoneProgress(RecordMixin, Base):
    __tablename__ = "milestone_progress"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "module_id", name="uq_milestone_progress_enrollment_module"
        ),
    )

    enrollment_id: Mapped[uuid.UUID] = fk("enrollment")
    module_id: Mapped[uuid.UUID] = fk("module")
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # locked | unlocked | complete
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
