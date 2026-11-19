"""Authoring behaviour against PostgreSQL (open questions 7.1).

Covers what the mock-based tests cannot: draft milestones stay hidden from interns until an admin
approves them, approval publishes them, components need a verified link and admin approval, and
material edits add a version instead of overwriting.

Run against a throwaway database (the dev database may be on an older schema):
  create a database, point MIGRATION_DATABASE_URL at it, run `alembic upgrade head`, then
  docker compose -f infra/compose.yml -f infra/compose.dev.yml run --rm -e RUN_INTEGRATION=1 \
      -e MIGRATION_DATABASE_URL=<url> api python -m pytest -q tests/integration/test_authoring_db.py
Everything runs in one transaction that is rolled back, so the database is left unchanged.
AI proposals are set up directly as job results; no model is called and no fixture is involved.
"""

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ProblemError
from app.modules.admin import catalog_service as catalog
from app.modules.admin import cohort_service as cohorts
from app.modules.admin import schemas as admin_s
from app.modules.admin.enrollment import sync_enrollment
from app.modules.audit.models import AuditLog
from app.modules.authoring import schemas as s
from app.modules.authoring import service
from app.modules.authoring.models import AiJob, AiJobKind, AiJobStatus, CourseMaterial
from app.modules.catalog import service as catalog_read
from app.modules.catalog.models import Course
from app.modules.catalog.roles import ensure_role_profiles
from app.modules.delivery.models import Cohort, Enrollment
from app.modules.identity.deps import Principal
from app.modules.identity.models import Role, RoleAssignment, User
from app.modules.progression.service import intern_dashboard

pytestmark = pytest.mark.skipif(os.environ.get("RUN_INTEGRATION") != "1", reason="integration test")


@dataclass
class World:
    trainer: Principal
    admin: Principal
    intern_id: uuid.UUID
    course_id: uuid.UUID
    first_module_id: uuid.UUID


def _user(db: Session, label: str) -> User:
    u = User(
        email=f"{label}-{uuid.uuid4().hex[:8]}@example.com", full_name=label, password_hash="x"
    )
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(get_settings().migration_database_url)  # owner role: bypasses RLS
    session = Session(engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


@pytest.fixture
def world(db: Session) -> World:
    ensure_role_profiles(db)
    trainer, admin, intern = _user(db, "trainer"), _user(db, "admin"), _user(db, "intern")
    p_trainer = Principal(trainer.id, frozenset({"trainer"}))
    p_admin = Principal(admin.id, frozenset({"admin"}))
    course = service.create_draft_course(
        db, p_trainer, s.CourseDraftIn(title="T course", role_profile="qa")
    )
    first = catalog.create_module(
        db,
        p_admin,
        course.id,
        admin_s.ModuleIn(title="Basics", description="d", learning_objective="o"),
    )
    first_id = first.modules[0].id
    catalog.create_task(
        db, p_admin, first_id, admin_s.TaskIn(title="Task one", description="do it")
    )
    cohort = Cohort(name="C")
    db.add(cohort)
    db.flush()
    enrollment = Enrollment(user_id=intern.id, cohort_id=cohort.id, course_id=course.id)
    db.add(enrollment)
    db.flush()
    sync_enrollment(db, enrollment)
    return World(p_trainer, p_admin, intern.id, course.id, first_id)


def _ready_job(
    db: Session, p: Principal, kind: AiJobKind, result: dict[str, Any], **fields: Any
) -> AiJob:
    job = AiJob(
        kind=kind, requester_id=p.user_id, status=AiJobStatus.ready, result=result, **fields
    )
    db.add(job)
    db.flush()
    return job


def _milestones_seen_by_intern(db: Session, w: World) -> int:
    dash = intern_dashboard(db, w.intern_id)
    assert dash is not None
    return len(dash.enrollments[0].milestones)


def test_draft_milestone_hidden_until_admin_approves(db: Session, world: World) -> None:
    w = world
    proposal = {
        "milestones": [
            {
                "title": "Advanced",
                "description": "d",
                "learning_objective": "o",
                "tasks": [
                    {
                        "title": "Hard task",
                        "task_type": "practical",
                        "description": "do it",
                        "learning_objective": "",
                        "submits": "a file",
                    }
                ],
            }
        ]
    }
    job = _ready_job(db, w.trainer, AiJobKind.draft_course, proposal, course_id=w.course_id)
    service.accept(db, w.trainer, job.id, s.AcceptRequest(items=[0]))

    new = catalog.course_tree(db, w.course_id).modules[-1]
    assert new.review_status == "draft" and len(new.tasks) == 1
    assert _milestones_seen_by_intern(db, w) == 1
    assert len(catalog_read.list_modules(db, w.course_id)) == 1

    catalog.approve_module(db, w.admin, new.id)
    assert _milestones_seen_by_intern(db, w) == 2
    logged = db.scalar(
        select(AuditLog.id).where(
            AuditLog.action == "module.approve", AuditLog.subject_id == new.id
        )
    )
    assert logged is not None


def _add_full_milestone(db: Session, w: World, title: str) -> None:
    tree = catalog.create_module(
        db,
        w.admin,
        w.course_id,
        admin_s.ModuleIn(title=title, description="d", learning_objective="o"),
    )
    catalog.create_task(
        db, w.admin, tree.modules[-1].id, admin_s.TaskIn(title=f"{title} task", description="x")
    )


def test_course_approval_needs_a_minimum_of_approved_milestones(db: Session, world: World) -> None:
    w = world  # the qa track needs 10; the fixture already has 1
    for n in range(2, 10):
        _add_full_milestone(db, w, f"M{n}")
    with pytest.raises(ProblemError) as info:  # 9 approved: too few
        catalog.update_course(
            db, w.admin, w.course_id, admin_s.CoursePatch(review_status="approved")
        )
    assert info.value.status == 409

    _add_full_milestone(db, w, "M10")
    # An unfinished draft milestone must not block approval, and must not count toward the minimum.
    catalog.create_module(
        db, w.trainer, w.course_id, admin_s.ModuleIn(title="Pending draft"), draft=True
    )
    approved = catalog.update_course(
        db, w.admin, w.course_id, admin_s.CoursePatch(review_status="approved")
    )
    assert approved.review_status == "approved"

    # More than the minimum is fine: courses can grow after approval.
    _add_full_milestone(db, w, "M11")
    again = catalog.update_course(
        db, w.admin, w.course_id, admin_s.CoursePatch(review_status="approved")
    )
    assert again.review_status == "approved"


def test_draft_milestones_do_not_count_toward_the_minimum(db: Session, world: World) -> None:
    w = world
    for n in range(2, 10):
        _add_full_milestone(db, w, f"M{n}")  # 9 approved
    catalog.create_module(
        db,
        w.trainer,
        w.course_id,
        admin_s.ModuleIn(title="Tenth, still draft", description="d", learning_objective="o"),
        draft=True,
    )
    with pytest.raises(ProblemError) as info:
        catalog.update_course(
            db, w.admin, w.course_id, admin_s.CoursePatch(review_status="approved")
        )
    assert info.value.status == 409


def test_cannot_approve_empty_milestone(db: Session, world: World) -> None:
    w = world
    tree = catalog.create_module(
        db, w.trainer, w.course_id, admin_s.ModuleIn(title="Bare"), draft=True
    )
    with pytest.raises(ProblemError) as info:
        catalog.approve_module(db, w.admin, tree.modules[-1].id)
    assert info.value.status == 409


def test_trainer_cannot_edit_approved_or_foreign_milestones(db: Session, world: World) -> None:
    w = world
    with pytest.raises(ProblemError) as info:
        service.update_module(db, w.trainer, w.first_module_id, admin_s.ModulePatch(title="Hacked"))
    assert info.value.status == 403
    # A draft made by the admin is also off limits to the trainer.
    other = catalog.create_module(
        db, w.admin, w.course_id, admin_s.ModuleIn(title="Admin draft"), draft=True
    )
    with pytest.raises(ProblemError):
        service.update_module(db, w.trainer, other.modules[-1].id, admin_s.ModulePatch(title="x"))
    # The trainer's own draft is editable.
    mine = catalog.create_module(
        db, w.trainer, w.course_id, admin_s.ModuleIn(title="Mine"), draft=True
    )
    out = service.update_module(
        db, w.trainer, mine.modules[-1].id, admin_s.ModulePatch(title="Mine v2")
    )
    assert out.modules[-1].title == "Mine v2"


def test_link_component_needs_verification_then_admin_approval(db: Session, world: World) -> None:
    w = world
    proposal = {
        "components": [
            {
                "type": "resource",
                "title": "Docs",
                "payload": {"url": "https://example.com/docs", "note": "n", "link_verified": False},
            }
        ]
    }
    job = _ready_job(
        db, w.trainer, AiJobKind.attach_components, proposal, module_id=w.first_module_id
    )
    service.accept(db, w.trainer, job.id, s.AcceptRequest(items=[0]))
    comp = service.list_components(db, w.trainer, w.first_module_id, None)[0]
    assert comp.review_status == "draft" and comp.ai_generated is True

    with pytest.raises(ProblemError) as info:
        service.approve_component(db, w.admin, comp.id)
    assert info.value.status == 409  # unverified link

    service.verify_link(db, w.trainer, comp.id)
    approved = service.approve_component(db, w.admin, comp.id)
    assert approved.review_status == "approved" and approved.approved_by == w.admin.user_id

    with pytest.raises(ProblemError) as blocked:  # trainers cannot change approved content
        service.update_component(db, w.trainer, comp.id, s.ComponentPatch(title="Changed"))
    assert blocked.value.status == 409


def test_other_trainers_cannot_see_or_change_a_component(db: Session, world: World) -> None:
    w = world
    comp = service.create_component(
        db,
        w.trainer,
        s.ComponentIn(
            module_id=w.first_module_id, type="reading_note", title="Note", payload={"body": "text"}
        ),
    )
    stranger = Principal(_user(db, "stranger").id, frozenset({"trainer"}))
    with pytest.raises(ProblemError) as info:
        service.update_component(db, stranger, comp.id, s.ComponentPatch(title="x"))
    assert info.value.status == 404
    assert service.list_components(db, stranger, w.first_module_id, None) == []


def test_accepted_edits_create_a_new_version(db: Session, world: World) -> None:
    w = world
    text = "Teh quick brown fox. Second sentence."
    mat = service.add_material(
        db, w.trainer, s.MaterialIn(module_id=w.first_module_id, filename="notes.md", text=text)
    )
    result = {
        "material_id": str(mat.id),
        "version": 1,
        "suggestions": [
            {
                "original": "Teh quick",
                "proposed": "The quick",
                "reason": "typo",
                "category": "correction",
            }
        ],
    }
    job = _ready_job(db, w.trainer, AiJobKind.improve_material, result, module_id=w.first_module_id)
    service.accept(db, w.trainer, job.id, s.AcceptRequest(items=[0]))

    versions = {
        m.version: m.extracted_text
        for m in db.scalars(select(CourseMaterial).where(CourseMaterial.filename == "notes.md"))
    }
    assert versions[1] == text  # original untouched
    assert (versions[2] or "").startswith("The quick")

    stale = _ready_job(
        db, w.trainer, AiJobKind.improve_material, result, module_id=w.first_module_id
    )
    with pytest.raises(
        ProblemError
    ) as info:  # version 2 exists now, so these suggestions are out of date
        service.accept(db, w.trainer, stale.id, s.AcceptRequest(items=[0]))
    assert info.value.status == 409


# ---------- Study material for learners ----------


def _intern(w: World) -> Principal:
    return Principal(w.intern_id, frozenset({"intern"}))


def _approved_note(db: Session, w: World, module_id: uuid.UUID, title: str) -> uuid.UUID:
    comp = service.create_component(
        db,
        w.trainer,
        s.ComponentIn(
            module_id=module_id, type="reading_note", title=title, payload={"body": "Read me"}
        ),
    )
    service.approve_component(db, w.admin, comp.id)
    return comp.id


def test_intern_sees_only_approved_study_material(db: Session, world: World) -> None:
    w = world
    approved = _approved_note(db, w, w.first_module_id, "Approved note")
    service.create_component(  # stays a draft
        db,
        w.trainer,
        s.ComponentIn(
            module_id=w.first_module_id, type="reading_note", title="Draft", payload={"body": "x"}
        ),
    )
    out = service.study_material(db, _intern(w), w.first_module_id)
    assert [i.id for i in out.items] == [approved]


def test_intern_cannot_open_a_locked_milestone(db: Session, world: World) -> None:
    w = world
    _add_full_milestone(db, w, "Second")  # approved, so it syncs as locked for the intern
    second = catalog.course_tree(db, w.course_id).modules[-1].id
    _approved_note(db, w, second, "Later note")
    with pytest.raises(ProblemError) as info:
        service.study_material(db, _intern(w), second)
    assert info.value.status == 403
    assert len(service.study_material(db, w.trainer, second).items) == 1  # staff can preview


def test_intern_outside_the_course_gets_not_found(db: Session, world: World) -> None:
    w = world
    _approved_note(db, w, w.first_module_id, "Note")
    stranger = Principal(_user(db, "other-intern").id, frozenset({"intern"}))
    with pytest.raises(ProblemError) as info:
        service.study_material(db, stranger, w.first_module_id)
    assert info.value.status == 404


def test_draft_milestone_has_no_study_view(db: Session, world: World) -> None:
    w = world
    tree = catalog.create_module(
        db, w.trainer, w.course_id, admin_s.ModuleIn(title="Hidden"), draft=True
    )
    with pytest.raises(ProblemError) as info:
        service.study_material(db, w.admin, tree.modules[-1].id)
    assert info.value.status == 404


def test_material_becomes_a_draft_reading_note(db: Session, world: World) -> None:
    w = world
    mat = service.add_material(
        db,
        w.trainer,
        s.MaterialIn(module_id=w.first_module_id, filename="week-1.md", text="Study this first."),
    )
    note = service.publish_material(db, w.trainer, mat.id, s.PublishMaterialIn())
    assert note.type == "reading_note" and note.review_status == "draft" and note.title == "week-1"
    assert (
        service.study_material(db, _intern(w), w.first_module_id).items == []
    )  # not until approved
    service.approve_component(db, w.admin, note.id)
    items = service.study_material(db, _intern(w), w.first_module_id).items
    assert len(items) == 1 and items[0].payload == {"body": "Study this first."}


@pytest.mark.parametrize("course_status", ["draft", "approved", "missing"])
def test_fr_hr_01_enrollment_requires_published_course(
    db: Session, world: World, course_status: str
) -> None:
    course = db.get(Course, world.course_id)
    assert course is not None
    assert course.review_status == "draft"
    if course_status == "approved":
        course.review_status = "approved"

    intern = _user(db, "new-intern")
    db.add(RoleAssignment(user_id=intern.id, role=Role.intern))
    cohort = Cohort(name="New cohort")
    db.add(cohort)
    db.flush()
    course_id = uuid.uuid4() if course_status == "missing" else course.id
    body = admin_s.EnrollmentIn(user_id=intern.id, course_id=course_id)

    if course_status == "approved":
        result = cohorts.enroll(db, world.admin, cohort.id, body)
        assert result.enrollment_count == 1
        dashboard = intern_dashboard(db, intern.id)
        assert dashboard is not None
        assert dashboard.enrollments[0].milestones[0].status == "unlocked"
        return

    with pytest.raises(ProblemError) as exc:
        cohorts.enroll(db, world.admin, cohort.id, body)
    assert exc.value.status == (409 if course_status == "draft" else 422)
    assert cohorts.cohort_detail(db, cohort.id).enrollment_count == 0


def test_fr_rev_03_trainer_reviews_pin_rubrics_and_unlock_next_milestone(
    db: Session, world: World
) -> None:
    from sqlalchemy import text

    from app.modules.catalog.models import RubricVersion, TaskTemplate
    from app.modules.delivery.models import TaskInstance, TaskInstanceStatus
    from app.modules.identity.deps import set_rls_context
    from app.modules.review import service as reviews
    from app.modules.review.schemas import ReviewInput
    from app.modules.submissions import service as submissions
    from app.modules.submissions.schemas import ArtifactIn, SubmissionIn

    enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == world.intern_id))
    assert enrollment is not None
    cohort = db.get(Cohort, enrollment.cohort_id)
    assert cohort is not None
    cohort.trainer_id = world.trainer.user_id
    other = Principal(_user(db, "other-trainer").id, frozenset({"trainer"}))
    intern = Principal(world.intern_id, frozenset({"intern"}))
    catalog.create_task(
        db,
        world.admin,
        world.first_module_id,
        admin_s.TaskIn(title="Second task", description="Another required task"),
    )
    course_tree = catalog.create_module(
        db,
        world.admin,
        world.course_id,
        admin_s.ModuleIn(title="Next", description="Next milestone", learning_objective="Learn"),
    )
    next_module = course_tree.modules[-1].id
    catalog.create_task(
        db,
        world.admin,
        next_module,
        admin_s.TaskIn(title="Later task", description="Later"),
    )
    tasks = db.execute(
        select(TaskInstance, TaskTemplate)
        .join(TaskTemplate, TaskTemplate.id == TaskInstance.task_template_id)
        .where(
            TaskInstance.enrollment_id == enrollment.id,
            TaskTemplate.module_id == world.first_module_id,
        )
        .order_by(TaskTemplate.title)
    ).all()
    assert len(tasks) == 2
    rubric = RubricVersion(
        rubric_key="test",
        version=1,
        published=True,
        content_hash=uuid.uuid4().hex,
        content={},
    )
    updated_rubric = RubricVersion(
        rubric_key="test",
        version=2,
        published=True,
        content_hash=uuid.uuid4().hex,
        content={},
    )
    db.add_all([rubric, updated_rubric])
    db.flush()
    for _, template in tasks:
        template.rubric_version_id = rubric.id
        template.deliverables = [{"id": "notes", "kind": "text", "required": True}]
    db.flush()

    db.execute(text("SET LOCAL ROLE aitms_app"))
    set_rls_context(db, intern)
    hand_in = SubmissionIn(
        artifacts=[ArtifactIn(deliverable_id="notes", kind="text", text="Draft")]
    )
    first, _ = submissions.create_submission(
        db, intern, tasks[0][0].id, hand_in, "first", get_settings()
    )
    replay, created = submissions.create_submission(
        db, intern, tasks[0][0].id, hand_in, "first", get_settings()
    )
    assert not created and replay.id == first.id

    set_rls_context(db, other)
    assert reviews.queue(db, other) == []
    with pytest.raises(ProblemError) as exc:
        reviews.decide(
            db,
            other,
            first.id,
            ReviewInput(
                decision="approve",
                reason="",
                rubric_version_id=rubric.id,
            ),
        )
    assert exc.value.status == 404

    # Simulate an admin publishing a replacement while this attempt waits.
    set_rls_context(db, world.admin)
    tasks[0][1].rubric_version_id = updated_rubric.id
    db.flush()
    set_rls_context(db, world.trainer)
    assert [row.submission_id for row in reviews.queue(db, world.trainer)] == [first.id]
    assert reviews.rubric_for_review(db, world.trainer, first.id).id == rubric.id
    with pytest.raises(ProblemError) as exc:
        reviews.decide(
            db,
            world.trainer,
            first.id,
            ReviewInput(
                decision="approve",
                reason="",
                rubric_version_id=updated_rubric.id,
            ),
        )
    assert exc.value.status == 409
    reviews.decide(
        db,
        world.trainer,
        first.id,
        ReviewInput(
            decision="request_revision",
            reason="Add acceptance criteria",
            rubric_version_id=rubric.id,
        ),
    )
    set_rls_context(db, intern)
    submission = submissions.get_submission(db, first.id)
    assert submission.review is not None
    assert submission.review.reason == "Add acceptance criteria"
    second, _ = submissions.create_submission(
        db, intern, tasks[0][0].id, hand_in, "second", get_settings()
    )
    remaining, _ = submissions.create_submission(
        db, intern, tasks[1][0].id, hand_in, "remaining", get_settings()
    )
    set_rls_context(db, world.trainer)
    with pytest.raises(ProblemError) as exc:
        reviews.decide(
            db,
            world.trainer,
            first.id,
            ReviewInput(
                decision="approve",
                reason="",
                rubric_version_id=rubric.id,
            ),
        )
    assert exc.value.status == 409
    approve = ReviewInput(decision="approve", reason="", rubric_version_id=updated_rubric.id)
    reviews.decide(db, world.trainer, second.id, approve)
    with pytest.raises(ProblemError) as exc:
        reviews.decide(db, world.trainer, second.id, approve)
    assert exc.value.status == 409
    assert tasks[0][0].status == TaskInstanceStatus.complete
    dashboard = intern_dashboard(db, world.intern_id)
    assert dashboard is not None
    assert [m.status for m in dashboard.enrollments[0].milestones] == ["unlocked", "locked"]

    reviews.decide(
        db,
        world.trainer,
        remaining.id,
        ReviewInput(
            decision="approve",
            reason="",
            rubric_version_id=rubric.id,
        ),
    )
    dashboard = intern_dashboard(db, world.intern_id)
    assert dashboard is not None
    assert [m.status for m in dashboard.enrollments[0].milestones] == ["complete", "unlocked"]
    assert reviews.queue(db, world.trainer) == []
