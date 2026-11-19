"""LLM gateway tables: llm_call, prompt_version, golden_sample."""

import enum
import uuid
from typing import Any

from sqlalchemy import Boolean, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import JSON, fk


class GoldenKind(str, enum.Enum):
    good = "good"
    average = "average"
    poor = "poor"
    adversarial = "adversarial"


class PromptVersion(RecordMixin, Base):
    __tablename__ = "prompt_version"

    prompt_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class LLMCall(RecordMixin, Base):
    __tablename__ = "llm_call"

    run_id: Mapped[uuid.UUID | None] = fk("evaluation_run", nullable=True)
    stage: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version_id: Mapped[uuid.UUID | None] = fk("prompt_version", nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GoldenSample(RecordMixin, Base):
    __tablename__ = "golden_sample"

    task_template_id: Mapped[uuid.UUID] = fk("task_template")
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[GoldenKind] = mapped_column(Enum(GoldenKind, name="golden_kind"), nullable=False)
    trainer_scores: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
