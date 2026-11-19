"""Row-level security on cohort and intern identifiers (Architecture 13.2). Human review required.

Model:
- The table owner (POSTGRES_USER) runs migrations and seed and bypasses RLS (ENABLE, not FORCE).
- The API connects as the non-owner role `aitms_app`, so every policy applies to it.
- Each request sets two transaction-local settings: app.user_id and app.roles (comma list).
  If they are missing, policies see no rows (fail closed).
- Helper functions are SECURITY DEFINER (owned by the table owner), so policies can look up
  cohort membership without recursive policy evaluation.

`upgrade_sql()` / `downgrade_sql()` are called from the Alembic baseline migration.
"""

APP_ROLE = "aitms_app"

# Tables the app role may use. Audit log is insert/select only (immutable).
APP_TABLES_RW = [
    "user",
    "session",
    "role_assignment",
    "role_profile",
    "course",
    "module",
    "task_template",
    "rubric_version",
    "cohort",
    "enrollment",
    "task_instance",
    "submission",
    "artifact",
    "evaluation_run",
    "stage_result",
    "criterion_score",
    "finding",
    "correction_task",
    "review_decision",
    "intervention",
    "message",
    "milestone_progress",
    "competency",
    "competency_score",
    "project",
    "project_artifact",
    "trace_node",
    "trace_edge",
    "prompt_version",
    "llm_call",
    "golden_sample",
    "outbox",
]

HELPERS = """
CREATE OR REPLACE FUNCTION app_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT nullif(current_setting('app.user_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION app_has_role(role_name text) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT role_name = ANY (string_to_array(coalesce(current_setting('app.roles', true), ''), ','))
$$;

CREATE OR REPLACE FUNCTION app_is_cohort_trainer(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM cohort c WHERE c.id = target AND c.trainer_id = app_user_id())
$$;

CREATE OR REPLACE FUNCTION app_is_cohort_member(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM enrollment e WHERE e.cohort_id = target AND e.user_id = app_user_id())
$$;

-- Can the current principal see this enrollment's work (submissions, evaluations)?
-- Intern: own. Trainer: cohorts they are assigned to. Admin: all. HR: not individual work.
CREATE OR REPLACE FUNCTION app_can_see_work(target_enrollment uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT app_has_role('admin') OR app_has_role('system') OR EXISTS (
    SELECT 1 FROM enrollment e
    WHERE e.id = target_enrollment
      AND (e.user_id = app_user_id()
           OR (app_has_role('trainer') AND app_is_cohort_trainer(e.cohort_id)))
  )
$$;

CREATE OR REPLACE FUNCTION app_task_instance_enrollment(target uuid) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT enrollment_id FROM task_instance WHERE id = target
$$;

CREATE OR REPLACE FUNCTION app_submission_enrollment(target uuid) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT ti.enrollment_id FROM submission s JOIN task_instance ti ON ti.id = s.task_instance_id
  WHERE s.id = target
$$;

CREATE OR REPLACE FUNCTION app_run_enrollment(target uuid) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT app_submission_enrollment(r.submission_id) FROM evaluation_run r WHERE r.id = target
$$;
"""

# (table, USING expression). The same expression is used WITH CHECK for writes.
POLICIES: list[tuple[str, str]] = [
    (
        "cohort",
        "app_has_role('admin') OR app_has_role('hr') OR app_has_role('system')"
        " OR (app_has_role('trainer') AND trainer_id = app_user_id())"
        " OR app_is_cohort_member(id)",
    ),
    (
        "enrollment",
        "app_has_role('admin') OR app_has_role('hr') OR app_has_role('system')"
        " OR user_id = app_user_id()"
        " OR (app_has_role('trainer') AND app_is_cohort_trainer(cohort_id))",
    ),
    ("task_instance", "app_has_role('hr') OR app_can_see_work(enrollment_id)"),
    ("submission", "app_can_see_work(app_task_instance_enrollment(task_instance_id))"),
    ("artifact", "app_can_see_work(app_submission_enrollment(submission_id))"),
    ("evaluation_run", "app_can_see_work(app_submission_enrollment(submission_id))"),
    ("stage_result", "app_can_see_work(app_run_enrollment(run_id))"),
    ("criterion_score", "app_can_see_work(app_run_enrollment(run_id))"),
    ("finding", "app_can_see_work(app_run_enrollment(run_id))"),
    ("correction_task", "app_can_see_work(app_run_enrollment(run_id))"),
    ("review_decision", "app_can_see_work(app_run_enrollment(run_id))"),
    ("milestone_progress", "app_has_role('hr') OR app_can_see_work(enrollment_id)"),
    ("message", "app_can_see_work(app_task_instance_enrollment(task_instance_id))"),
    ("intervention", "app_can_see_work(app_task_instance_enrollment(task_instance_id))"),
]


def upgrade_sql() -> list[str]:
    statements = [HELPERS]
    for table, expr in POLICIES:
        statements.append(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        statements.append(f'CREATE POLICY scoped ON "{table}" USING ({expr}) WITH CHECK ({expr})')
    tables = ", ".join(f'"{t}"' for t in APP_TABLES_RW)
    statements += [
        f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tables} TO {APP_ROLE}",
        f'GRANT SELECT, INSERT ON "audit_log" TO {APP_ROLE}',
    ]
    return statements


def downgrade_sql() -> list[str]:
    statements = [f'DROP POLICY IF EXISTS scoped ON "{t}"' for t, _ in POLICIES]
    statements += [f'ALTER TABLE "{t}" DISABLE ROW LEVEL SECURITY' for t, _ in POLICIES]
    statements += [
        f"DROP FUNCTION IF EXISTS {fn} CASCADE"
        for fn in (
            "app_run_enrollment(uuid)",
            "app_submission_enrollment(uuid)",
            "app_task_instance_enrollment(uuid)",
            "app_can_see_work(uuid)",
            "app_is_cohort_member(uuid)",
            "app_is_cohort_trainer(uuid)",
            "app_has_role(text)",
            "app_user_id()",
        )
    ]
    return statements
