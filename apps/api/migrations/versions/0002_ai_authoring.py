"""AI-assisted authoring: ai_job, course_material, course_component.

Matches app/modules/authoring/models.py. Human review required (second engineer).
Open questions section 7 (A1 to A8).

Revision ID: 0002_ai_authoring
Revises: 0001_baseline
Create Date: 2026-11-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID

revision = "0002_ai_authoring"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)
APP_ROLE = "aitms_app"
JOB_KIND = ("draft_course", "improve_material", "attach_components")
JOB_STATUS = ("queued", "running", "ready", "accepted", "dismissed", "failed")
COMPONENT = (
    "resource",
    "reading_note",
    "quiz",
    "starter_file",
    "deliverable_manifest",
    "rubric_draft",
)


def _common() -> list[sa.Column]:
    return [
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TZ, server_default=sa.func.now(), nullable=False),
    ]


def _fk(table: str, name: str, target: str, nullable: bool) -> sa.Column:
    return sa.Column(
        name,
        UUID(as_uuid=True),
        sa.ForeignKey(f"{target}.id", name=f"fk_{table}_{name}_{target}"),
        nullable=nullable,
    )


def upgrade() -> None:
    op.execute("CREATE TYPE ai_job_kind AS ENUM (%s)" % ", ".join(f"'{v}'" for v in JOB_KIND))
    op.execute("CREATE TYPE ai_job_status AS ENUM (%s)" % ", ".join(f"'{v}'" for v in JOB_STATUS))
    op.execute("CREATE TYPE component_type AS ENUM (%s)" % ", ".join(f"'{v}'" for v in COMPONENT))

    op.create_table(
        "ai_job",
        *_common(),
        sa.Column("kind", ENUM(*JOB_KIND, name="ai_job_kind", create_type=False), nullable=False),
        sa.Column(
            "status",
            ENUM(*JOB_STATUS, name="ai_job_status", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        _fk("ai_job", "requester_id", "user", False),
        _fk("ai_job", "course_id", "course", True),
        _fk("ai_job", "module_id", "module", True),
        _fk("ai_job", "task_id", "task_template", True),
        sa.Column("input", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ai_job"),
    )
    for col in ("requester_id", "course_id", "module_id", "task_id"):
        op.create_index(f"ix_ai_job_{col}", "ai_job", [col])

    op.create_table(
        "course_material",
        *_common(),
        _fk("course_material", "module_id", "module", True),
        _fk("course_material", "task_id", "task_template", True),
        _fk("course_material", "uploaded_by", "user", False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_course_material"),
    )
    for col in ("module_id", "task_id", "uploaded_by"):
        op.create_index(f"ix_course_material_{col}", "course_material", [col])

    op.create_table(
        "course_component",
        *_common(),
        _fk("course_component", "module_id", "module", True),
        _fk("course_component", "task_id", "task_template", True),
        sa.Column(
            "type", ENUM(*COMPONENT, name="component_type", create_type=False), nullable=False
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("ai_generated", sa.Boolean, nullable=False, server_default="false"),
        _fk("course_component", "ai_job_id", "ai_job", True),
        _fk("course_component", "created_by", "user", False),
        _fk("course_component", "approved_by", "user", True),
        sa.Column("approved_at", TZ, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_course_component"),
    )
    for col in ("module_id", "task_id", "ai_job_id", "created_by", "approved_by"):
        op.create_index(f"ix_course_component_{col}", "course_component", [col])

    # Row scoping: a trainer sees only their own jobs; admin and the worker see all.
    op.execute('ALTER TABLE "ai_job" ENABLE ROW LEVEL SECURITY')
    expr = "app_has_role('admin') OR app_has_role('system') OR requester_id = app_user_id()"
    op.execute(f'CREATE POLICY scoped ON "ai_job" USING ({expr}) WITH CHECK ({expr})')
    op.execute(
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON "ai_job", "course_material", "course_component" '
        f"TO {APP_ROLE}"
    )


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS scoped ON "ai_job"')
    for table in ("course_component", "course_material", "ai_job"):
        op.drop_table(table)
    for enum in ("component_type", "ai_job_status", "ai_job_kind"):
        op.execute(f"DROP TYPE IF EXISTS {enum}")
