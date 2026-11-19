"""Per-module review status: draft modules stay hidden from interns until an admin approves.

Existing modules become 'approved' so nothing visible to interns changes.
Human review required (second engineer). Open questions section 7.

Revision ID: 0003_module_review_status
Revises: 0002_ai_authoring
Create Date: 2026-11-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_module_review_status"
down_revision = "0002_ai_authoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "module",
        sa.Column("review_status", sa.String(20), nullable=False, server_default="approved"),
    )
    op.add_column(
        "module",
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", name="fk_module_created_by_user"),
            nullable=True,
        ),
    )
    op.create_index("ix_module_created_by", "module", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_module_created_by", table_name="module")
    op.drop_column("module", "created_by")
    op.drop_column("module", "review_status")
