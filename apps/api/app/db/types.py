"""Shared column helpers."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

JSON = JSONB


def fk(target: str, *, nullable: bool = False, index: bool = True) -> Mapped[uuid.UUID]:
    """Foreign key to <table>.id."""
    return mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{target}.id"), nullable=nullable, index=index
    )


def json_col(default: Any = None, *, nullable: bool = False) -> Mapped[Any]:
    return mapped_column(JSONB, nullable=nullable, default=default)
