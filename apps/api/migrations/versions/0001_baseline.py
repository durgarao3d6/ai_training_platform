"""Baseline schema v1: all module tables, immutability triggers, row-level security.

Hand-written to match app/modules/*/models.py and the naming convention in app/db/base.py.
Human review required (second engineer). Requirements: 3.3, 4.1, 2.1.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db import rls

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def _common() -> list[sa.Column]:
    return [
        sa.Column(
            "id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("created_at", TZ, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TZ, server_default=sa.func.now(), nullable=False),
    ]


class _T:
    """Collects columns for one table and applies the naming convention."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.items: list[sa.Column | sa.Constraint] = _common()
        self.indexes: list[str] = []

    def col(
        self,
        name: str,
        type_: sa.types.TypeEngine,
        nullable: bool = False,
        *,
        unique: bool = False,
        index: bool = False,
        server_default: str | None = None,
    ) -> "_T":
        sd = sa.text(server_default) if server_default is not None else None
        self.items.append(sa.Column(name, type_, nullable=nullable, server_default=sd))
        if unique:
            self.items.append(sa.UniqueConstraint(name, name=f"uq_{self.name}_{name}"))
        if index:
            self.indexes.append(name)
        return self

    def fk(self, name: str, target: str, nullable: bool = False) -> "_T":
        self.items.append(
            sa.Column(
                name,
                UUID(as_uuid=True),
                sa.ForeignKey(f"{target}.id", name=f"fk_{self.name}_{name}_{target}"),
                nullable=nullable,
            )
        )
        self.indexes.append(name)
        return self

    def unique(self, name: str, *cols: str) -> "_T":
        self.items.append(sa.UniqueConstraint(*cols, name=name))
        return self

    def create(self) -> None:
        op.create_table(
            self.name, *self.items, sa.PrimaryKeyConstraint("id", name=f"pk_{self.name}")
        )
        for column in self.indexes:
            op.create_index(f"ix_{self.name}_{column}", self.name, [column])


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name)


S = sa.String
TEXT = sa.Text()
INT = sa.Integer()
FLOAT = sa.Float()
BOOL = sa.Boolean()


def upgrade() -> None:
    # ---------- Identity ----------
    (
        _T("user")
        .col("email", S(320), unique=True)
        .col("full_name", S(200))
        .col("password_hash", S(255))
        .col("failed_login_count", INT, server_default="0")
        .col("locked_until", TZ, True)
        .create()
    )
    (
        _T("role_assignment")
        .fk("user_id", "user")
        .col("role", _enum("role", "intern", "trainer", "hr", "admin"))
        .unique("uq_role_assignment_user_role", "user_id", "role")
        .create()
    )
    (
        _T("session")
        .fk("user_id", "user")
        .col("refresh_token_hash", S(128), unique=True)
        .col("expires_at", TZ)
        .col("revoked_at", TZ, True)
        .create()
    )

    # ---------- Catalog ----------
    (
        _T("role_profile")
        .col("key", S(50), unique=True)
        .col("name", S(100))
        .col("checker_keys", JSONB)
        .col("judge_prompt_key", S(100), True)
        .col("review_policy", JSONB)
        .create()
    )
    (
        _T("course")
        .fk("role_profile_id", "role_profile")
        .col("key", S(100), unique=True)
        .col("title", S(200))
        .col("description", TEXT)
        .col("review_status", S(20), server_default="'draft'")
        .col("final_deliverable", TEXT)
        .create()
    )
    (
        _T("module")
        .fk("course_id", "course")
        .col("key", S(100), unique=True)
        .col("title", S(200))
        .col("position", INT)
        .col("description", TEXT)
        .col("learning_objective", TEXT)
        .unique("uq_module_course_position", "course_id", "position")
        .create()
    )
    (
        _T("rubric_version")
        .col("rubric_key", S(100), index=True)
        .col("version", INT)
        .col("content_hash", S(64), unique=True)
        .col("content", JSONB)
        .col("published", BOOL, server_default="false")
        .unique("uq_rubric_version_key_version", "rubric_key", "version")
        .create()
    )
    (
        _T("task_template")
        .fk("module_id", "module")
        .col("key", S(100), unique=True)
        .col("title", S(200))
        .col("task_type", _enum("task_type", "practical", "integration", "assessment"))
        .col("description", TEXT)
        .col("learning_objective", TEXT)
        .col("deliverables", JSONB)
        .col("depth", _enum("task_depth", "demo", "content"))
        .fk("rubric_version_id", "rubric_version", nullable=True)
        .col("submits", TEXT)
        .col("evaluated_on", TEXT)
        .col("requires_review", BOOL, server_default="false")
        .col("starter_files", JSONB)
        .create()
    )

    # ---------- Delivery ----------
    (
        _T("cohort")
        .col("name", S(200))
        .col("starts_on", sa.Date(), True)
        .fk("trainer_id", "user", nullable=True)
        .create()
    )
    (
        _T("enrollment")
        .fk("user_id", "user")
        .fk("cohort_id", "cohort")
        .fk("course_id", "course")
        .unique("uq_enrollment_user_course", "user_id", "course_id")
        .create()
    )
    (
        _T("task_instance")
        .fk("enrollment_id", "enrollment")
        .fk("task_template_id", "task_template")
        .col(
            "status",
            _enum(
                "task_instance_status",
                "locked",
                "unlocked",
                "in_progress",
                "needs_another_pass",
                "review_pending",
                "complete",
            ),
        )
        .unique("uq_task_instance_enrollment_task", "enrollment_id", "task_template_id")
        .create()
    )

    # ---------- Submissions ----------
    (
        _T("submission")
        .fk("task_instance_id", "task_instance")
        .col("attempt_number", INT)
        .col("idempotency_key", S(100), True)
        .col(
            "status", _enum("submission_status", "received", "evaluating", "evaluated", "rejected")
        )
        .unique("uq_submission_task_instance_attempt", "task_instance_id", "attempt_number")
        .unique("uq_submission_task_instance_idem", "task_instance_id", "idempotency_key")
        .create()
    )
    (
        _T("artifact")
        .fk("submission_id", "submission")
        .col("deliverable_id", S(100))
        .col("kind", _enum("artifact_kind", "file", "link", "text"))
        .col("content_type", S(200), True)
        .col("sha256", S(64), True)
        .col("size_bytes", sa.BigInteger(), True)
        .col("storage_key", S(500), True)
        .col("filename", S(255), True)
        .col("url", S(2000), True)
        .col("text_content", TEXT, True)
        .create()
    )
    (
        _T("outbox")
        .col("topic", S(100), index=True)
        .col("payload", JSONB)
        .col("published_at", TZ, True)
        .create()
    )

    # ---------- Evaluation ----------
    (
        _T("evaluation_run")
        .fk("submission_id", "submission")
        .fk("rubric_version_id", "rubric_version")
        .col(
            "state",
            _enum(
                "run_state",
                "SUBMITTED",
                "VALIDATED",
                "COMPLETENESS_CHECKED",
                "AUTOCHECKED",
                "AI_RUBRIC",
                "SCORED",
                "FEEDBACK",
                "CORRECTION_CREATED",
                "HUMAN_REVIEW",
                "APPROVED",
                "REVISION_REQUIRED",
                "ERROR_RETRYING",
                "NEEDS_HUMAN",
            ),
        )
        .col("prompt_versions", JSONB)
        .col("model_id", S(100), True)
        .col("tool_versions", JSONB)
        .col("runner_image_versions", JSONB)
        .col("total_score", FLOAT, True)
        .col("outcome", S(30), True)
        .col("review_reasons", JSONB)
        .col("retry_count", INT, server_default="0")
        .create()
    )
    (
        _T("stage_result")
        .fk("run_id", "evaluation_run")
        .col("stage", S(50))
        .col("input_hash", S(64))
        .col("output", JSONB)
        .col("status", S(20))
        .unique("uq_stage_result_run_stage_input", "run_id", "stage", "input_hash")
        .create()
    )
    (
        _T("criterion_score")
        .fk("run_id", "evaluation_run")
        .col("criterion_id", S(100))
        .col("llm_rating", INT, True)
        .col("final_rating", INT)
        .col("weight", INT)
        .col("points", FLOAT)
        .col("rationale", TEXT)
        .col("evidence", JSONB)
        .col("evidence_verified", BOOL)
        .unique("uq_criterion_score_run_criterion", "run_id", "criterion_id")
        .create()
    )
    (
        _T("finding")
        .fk("run_id", "evaluation_run")
        .col("source", _enum("finding_source", "tool", "ai", "trainer"))
        .col("checker_key", S(100), True)
        .col("severity", _enum("severity", "info", "warning", "blocking"))
        .col("criterion_id", S(100), True)
        .col("message", TEXT)
        .col("data", JSONB)
        .col("rating_cap", INT, True)
        .create()
    )
    (
        _T("correction_task")
        .fk("run_id", "evaluation_run")
        .col("criterion_id", S(100))
        .col("template_key", S(100))
        .col("body", TEXT)
        .col("status", S(20))
        .create()
    )

    # ---------- Review ----------
    (
        _T("review_decision")
        .fk("run_id", "evaluation_run")
        .fk("reviewer_id", "user")
        .col("decision", _enum("decision", "approve", "request_revision", "override"))
        .col("reason", TEXT, True)
        .create()
    )
    (
        _T("intervention")
        .fk("task_instance_id", "task_instance")
        .fk("trainer_id", "user")
        .col("note", TEXT)
        .create()
    )
    (
        _T("message")
        .fk("task_instance_id", "task_instance")
        .fk("sender_id", "user")
        .fk("recipient_id", "user", nullable=True)
        .col("body", TEXT)
        .col("is_disagreement", BOOL)
        .create()
    )

    # ---------- Progression and competency ----------
    (
        _T("milestone_progress")
        .fk("enrollment_id", "enrollment")
        .fk("module_id", "module")
        .col("status", S(20))
        .col("completed_at", TZ, True)
        .unique("uq_milestone_progress_enrollment_module", "enrollment_id", "module_id")
        .create()
    )
    (
        _T("competency")
        .fk("role_profile_id", "role_profile")
        .col("key", S(100), unique=True)
        .col("name", S(200))
        .col("description", TEXT)
        .create()
    )
    (
        _T("competency_score")
        .fk("user_id", "user")
        .fk("competency_id", "competency")
        .fk("run_id", "evaluation_run")
        .col("score", FLOAT)
        .create()
    )

    # ---------- Traceability ----------
    _T("project").col("name", S(200)).col("description", TEXT).create()
    (
        _T("project_artifact")
        .fk("project_id", "project")
        .fk("submission_id", "submission")
        .col("role_key", S(50))
        .create()
    )
    (
        _T("trace_node")
        .fk("project_id", "project")
        .col(
            "type",
            _enum(
                "node_type",
                "requirement",
                "story",
                "acceptance_criterion",
                "design_frame",
                "endpoint",
                "dev_task",
                "test_case",
                "defect",
            ),
        )
        .col("external_ref", S(200))
        .col("version", INT)
        .create()
    )
    (
        _T("trace_edge")
        .fk("from_node_id", "trace_node")
        .fk("to_node_id", "trace_node")
        .col(
            "relation",
            _enum("relation", "satisfies", "designs", "implements", "verifies", "reveals"),
        )
        .col("status", _enum("edge_status", "proposed", "confirmed", "rejected"))
        .fk("confirmed_by", "user", nullable=True)
        .col("origin", _enum("edge_origin", "tag", "suggested", "manual"))
        .create()
    )

    # ---------- LLM gateway ----------
    (
        _T("prompt_version")
        .col("prompt_key", S(100), index=True)
        .col("content_hash", S(64), unique=True)
        .col("content", TEXT)
        .create()
    )
    (
        _T("llm_call")
        .fk("run_id", "evaluation_run", nullable=True)
        .col("stage", S(50), True)
        .col("model", S(100))
        .fk("prompt_version_id", "prompt_version", nullable=True)
        .col("input_hash", S(64), index=True)
        .col("prompt_tokens", INT)
        .col("completion_tokens", INT)
        .col("cost_usd", FLOAT)
        .col("latency_ms", INT)
        .col("cache_hit", BOOL)
        .create()
    )
    (
        _T("golden_sample")
        .fk("task_template_id", "task_template")
        .col("label", S(200))
        .col("kind", _enum("golden_kind", "good", "average", "poor", "adversarial"))
        .col("trainer_scores", JSONB)
        .col("content", JSONB)
        .create()
    )

    # ---------- Audit ----------
    (
        _T("audit_log")
        .fk("actor_id", "user", nullable=True)
        .col("action", S(100), index=True)
        .col("subject_type", S(100))
        .col("subject_id", UUID(as_uuid=True), True, index=True)
        .col("before", JSONB, True)
        .col("after", JSONB, True)
        .col("reason", TEXT, True)
        .create()
    )

    # ---------- Triggers ----------
    # Published rubric versions are immutable (Req 3.3). Publishing itself (false -> true) is allowed.
    op.execute("""
    CREATE FUNCTION rubric_version_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.published THEN
        RAISE EXCEPTION 'rubric_version % is published and cannot be changed', OLD.id
          USING ERRCODE = 'restrict_violation';
      END IF;
      RETURN COALESCE(NEW, OLD);
    END $$;
    CREATE TRIGGER rubric_version_immutable BEFORE UPDATE OR DELETE ON rubric_version
      FOR EACH ROW EXECUTE FUNCTION rubric_version_immutable();
    """)
    # The audit log is append-only.
    op.execute("""
    CREATE FUNCTION audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'audit_log is append-only' USING ERRCODE = 'restrict_violation';
    END $$;
    CREATE TRIGGER audit_log_append_only BEFORE UPDATE OR DELETE ON audit_log
      FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
    """)

    # Earlier attempts are immutable (Req 6.3): artifacts never change, and a submission's
    # identity (task instance, attempt number, idempotency key) is fixed. Status may change.
    op.execute("""
    CREATE FUNCTION artifact_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'artifacts are immutable' USING ERRCODE = 'restrict_violation';
    END $$;
    CREATE TRIGGER artifact_immutable BEFORE UPDATE OR DELETE ON artifact
      FOR EACH ROW EXECUTE FUNCTION artifact_immutable();

    CREATE FUNCTION submission_identity_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'submissions cannot be deleted' USING ERRCODE = 'restrict_violation';
      END IF;
      IF NEW.task_instance_id IS DISTINCT FROM OLD.task_instance_id
         OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
         OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key THEN
        RAISE EXCEPTION 'submission % identity cannot change', OLD.id USING ERRCODE = 'restrict_violation';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER submission_identity_immutable BEFORE UPDATE OR DELETE ON submission
      FOR EACH ROW EXECUTE FUNCTION submission_identity_immutable();
    """)

    # ---------- Row-level security and app role grants ----------
    for statement in rls.upgrade_sql():
        op.execute(statement)


TABLES_REVERSE = [
    "audit_log",
    "golden_sample",
    "llm_call",
    "prompt_version",
    "trace_edge",
    "trace_node",
    "project_artifact",
    "project",
    "competency_score",
    "competency",
    "milestone_progress",
    "message",
    "intervention",
    "review_decision",
    "correction_task",
    "finding",
    "criterion_score",
    "stage_result",
    "evaluation_run",
    "outbox",
    "artifact",
    "submission",
    "task_instance",
    "enrollment",
    "cohort",
    "task_template",
    "rubric_version",
    "module",
    "course",
    "role_profile",
    "session",
    "role_assignment",
    "user",
]

ENUMS = [
    "role",
    "task_type",
    "task_depth",
    "task_instance_status",
    "submission_status",
    "artifact_kind",
    "run_state",
    "finding_source",
    "severity",
    "decision",
    "node_type",
    "relation",
    "edge_status",
    "edge_origin",
    "golden_kind",
]


def downgrade() -> None:
    for statement in rls.downgrade_sql():
        op.execute(statement)
    op.execute("DROP TRIGGER IF EXISTS submission_identity_immutable ON submission")
    op.execute("DROP FUNCTION IF EXISTS submission_identity_immutable()")
    op.execute("DROP TRIGGER IF EXISTS artifact_immutable ON artifact")
    op.execute("DROP FUNCTION IF EXISTS artifact_immutable()")
    op.execute("DROP TRIGGER IF EXISTS audit_log_append_only ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_append_only()")
    op.execute("DROP TRIGGER IF EXISTS rubric_version_immutable ON rubric_version")
    op.execute("DROP FUNCTION IF EXISTS rubric_version_immutable()")
    for table in TABLES_REVERSE:
        op.drop_table(table)
    for enum in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
