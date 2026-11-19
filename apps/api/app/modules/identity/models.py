"""Identity/RBAC tables: user, session, role_assignment."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, RecordMixin
from app.db.types import fk


class Role(str, enum.Enum):
    intern = "intern"
    trainer = "trainer"
    hr = "hr"
    admin = "admin"


class User(RecordMixin, Base):
    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    failed_login_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RoleAssignment(RecordMixin, Base):
    __tablename__ = "role_assignment"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_role_assignment_user_role"),)

    user_id: Mapped[uuid.UUID] = fk("user")
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), nullable=False)


class Session(RecordMixin, Base):
    __tablename__ = "session"

    user_id: Mapped[uuid.UUID] = fk("user")
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
