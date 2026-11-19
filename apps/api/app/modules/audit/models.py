"""Audit tables: audit_log. Immutable: a trigger rejects UPDATE and DELETE."""

import uuid
from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import JSON, fk


class AuditLog(RecordMixin, Base):
    __tablename__ = "audit_log"

    actor_id: Mapped[uuid.UUID | None] = fk("user", nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
