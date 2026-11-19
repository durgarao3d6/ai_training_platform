"""Transactional outbox (Architecture 16).

Work is enqueued by inserting an outbox row in the same transaction as the record it is about,
so a submission can never exist without its event, and an event never refers to a rolled-back
row. A relay (worker) publishes unpublished rows to the queue and sets published_at.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import JSON


class OutboxEvent(RecordMixin, Base):
    __tablename__ = "outbox"

    topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def enqueue(db: Session, topic: str, payload: dict[str, Any]) -> OutboxEvent:
    """Add an event to the current transaction. It is only visible once the caller commits."""
    event = OutboxEvent(topic=topic, payload=payload)
    db.add(event)
    return event
