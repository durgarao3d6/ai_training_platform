"""Competency tables: competency, competency_score. Scores come from approved results only."""

import uuid

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import fk


class Competency(RecordMixin, Base):
    __tablename__ = "competency"

    role_profile_id: Mapped[uuid.UUID] = fk("role_profile")
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class CompetencyScore(RecordMixin, Base):
    """History is kept: each approved run adds a row."""

    __tablename__ = "competency_score"

    user_id: Mapped[uuid.UUID] = fk("user")
    competency_id: Mapped[uuid.UUID] = fk("competency")
    run_id: Mapped[uuid.UUID] = fk("evaluation_run")
    score: Mapped[float] = mapped_column(Float, nullable=False)
