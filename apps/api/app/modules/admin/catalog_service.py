"""Course authoring in the application (FR-CAT-01, FR-CAT-05).

Rules:
- Keys are generated from titles once and never change; they are stable machine identifiers.
- Adding milestones or tasks syncs every enrolled intern (new progress rows and task instances).
- Nothing an intern has submitted against is ever deleted: removing a task or milestone with
  submissions is refused (409).
- A course can be marked approved only when it passes the catalog acceptance checks
  (tech lead decision 1).
- Rubrics: one editable draft per task. Publishing validates it fully (schema, five levels,
  weights 100, registered checkers, correction templates), freezes it (DB trigger) and writes an
  audit entry. Changing a published rubric means editing a new draft and publishing version n+1.
"""

import re
import uuid
from typing import Any

from fastapi import status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.content.validator import deliverable_errors, validate_rubric
from app.core.errors import ProblemError
from app.modules.admin import schemas as s
from app.modules.admin.enrollment import sync_course
from app.modules.audit.models import AuditLog
from app.modules.catalog.content import DEFAULT_DELIVERABLES, EXPECTED_MILESTONES, rubric_hash
from app.modules.catalog.models import (
    Course,
    Module,
    RoleProfile,
    RubricVersion,
    TaskDepth,
    TaskTemplate,
    TaskType,
)
from app.modules.catalog.roles import checker_registry
from app.modules.catalog.schemas import CriterionOut, deliverable_out
from app.modules.delivery.models import Enrollment, TaskInstance
from app.modules.identity.deps import Principal
from app.modules.progression.models import MilestoneProgress
from app.modules.submissions.models import Submission

_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(text: str, limit: int = 40) -> str:
    return _SLUG.sub("_", text.lower()).strip("_")[:limit].strip("_") or "item"


def _unique_key(db: Session, model: Any, base: str) -> str:
    key, n = base, 2
    while db.scalar(select(model.id).where(model.key == key)) is not None:
        key = f"{base}_{n}"
        n += 1
    return key


def _not_found(what: str) -> ProblemError:
    return ProblemError(status.HTTP_404_NOT_FOUND, f"{what} not found")


def _get(db: Session, model: Any, id_: uuid.UUID, what: str) -> Any:
    row = db.get(model, id_)
    if row is None:
        raise _not_found(what)
    return row


def _audit(
    db: Session,
    principal: Principal,
    action: str,
    subject: Any,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=principal.user_id,
            action=action,
            subject_type=subject.__tablename__,
            subject_id=subject.id,
            after=after,
            reason=reason,
        )
    )


# ---------- Read models ----------


def role_profiles(db: Session) -> list[s.RoleProfileOut]:
    return [
        s.RoleProfileOut(
            key=r.key,
            name=r.name,
            checkers=list(r.checker_keys),
            always_review=bool(r.review_policy.get("always_review")),
        )
        for r in db.scalars(select(RoleProfile).order_by(RoleProfile.name))
    ]


def list_courses(db: Session) -> list[s.CourseSummaryOut]:
    out = []
    for course, role_key in db.execute(
        select(Course, RoleProfile.key)
        .join(RoleProfile, RoleProfile.id == Course.role_profile_id)
        .order_by(Course.title)
    ):
        module_ids = list(db.scalars(select(Module.id).where(Module.course_id == course.id)))
        out.append(
            s.CourseSummaryOut(
                id=course.id,
                key=course.key,
                title=course.title,
                role_profile=role_key,
                review_status=course.review_status,
                milestone_count=len(module_ids),
                task_count=db.scalar(
                    select(func.count())
                    .select_from(TaskTemplate)
                    .where(TaskTemplate.module_id.in_(module_ids))
                )
                or 0
                if module_ids
                else 0,
                enrollment_count=db.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .where(Enrollment.course_id == course.id)
                )
                or 0,
                updated_at=course.updated_at,
            )
        )
    return out


def _rubric_admin(row: RubricVersion | None) -> s.RubricOutAdmin | None:
    if row is None:
        return None
    content = row.content
    return s.RubricOutAdmin(
        id=row.id,
        version=row.version,
        published=row.published,
        pass_threshold=content.get("pass_threshold", 70),
        criteria=[
            CriterionOut(
                id=c["id"],
                title=c.get("title") or c["id"],
                weight=c.get("weight", 0),
                mandatory=c.get("mandatory_min_level") is not None,
                mandatory_min_level=c.get("mandatory_min_level"),
                levels=c.get("levels", {}),
            )
            for c in content.get("criteria", [])
        ],
        checkers=content.get("checkers", []),
        content=content,
    )


def _draft_for(db: Session, task: TaskTemplate) -> RubricVersion | None:
    return db.scalar(
        select(RubricVersion).where(
            RubricVersion.rubric_key == task.key, RubricVersion.published.is_(False)
        )
    )


def _task_out(db: Session, task: TaskTemplate) -> s.TaskAdminOut:
    published = db.get(RubricVersion, task.rubric_version_id) if task.rubric_version_id else None
    return s.TaskAdminOut(
        id=task.id,
        key=task.key,
        title=task.title,
        task_type=task.task_type.value,
        depth=task.depth.value,
        description=task.description,
        learning_objective=task.learning_objective,
        submits=task.submits,
        evaluated_on=task.evaluated_on,
        requires_review=task.requires_review,
        deliverables=[deliverable_out(d) for d in task.deliverables],
        published_rubric=_rubric_admin(published),
        draft_rubric=_rubric_admin(_draft_for(db, task)),
    )


def course_tree(db: Session, course_id: uuid.UUID) -> s.CourseAdminOut:
    course = _get(db, Course, course_id, "Course")
    role = db.get(RoleProfile, course.role_profile_id)
    modules = db.scalars(
        select(Module).where(Module.course_id == course.id).order_by(Module.position)
    ).all()
    return s.CourseAdminOut(
        id=course.id,
        key=course.key,
        title=course.title,
        role_profile=role.key if role else "",
        description=course.description,
        final_deliverable=course.final_deliverable,
        review_status=course.review_status,
        enrollment_count=db.scalar(
            select(func.count()).select_from(Enrollment).where(Enrollment.course_id == course.id)
        )
        or 0,
        modules=[
            s.ModuleAdminOut(
                id=m.id,
                key=m.key,
                title=m.title,
                position=m.position,
                description=m.description,
                learning_objective=m.learning_objective,
                review_status=m.review_status,
                created_by=m.created_by,
                tasks=[
                    _task_out(db, t)
                    for t in db.scalars(
                        select(TaskTemplate)
                        .where(TaskTemplate.module_id == m.id)
                        .order_by(TaskTemplate.created_at)
                    )
                ],
            )
            for m in modules
        ],
    )


# ---------- Courses ----------


def _approval_problems(db: Session, course: Course, role_key: str) -> list[str]:
    """Catalog acceptance checks (tech lead decision 1) on the stored course."""
    problems: list[str] = []
    # Only approved milestones count: drafts are invisible to interns and are checked when approved.
    # The track's milestone count is a minimum, so approved courses can grow (open question 10).
    modules = db.scalars(
        select(Module).where(Module.course_id == course.id, Module.review_status == "approved")
    ).all()
    expected = EXPECTED_MILESTONES.get(role_key)
    if expected is not None and len(modules) < expected:
        problems.append(
            f"The course needs at least {expected} approved milestones; it has {len(modules)}."
        )
    for m in modules:
        if not m.description.strip():
            problems.append(f"Milestone “{m.title}” needs a description.")
        if not m.learning_objective.strip():
            problems.append(f"Milestone “{m.title}” needs a learning objective.")
        if (
            db.scalar(select(TaskTemplate.id).where(TaskTemplate.module_id == m.id).limit(1))
            is None
        ):
            problems.append(f"Milestone “{m.title}” needs a task.")
    return problems


def create_course(db: Session, principal: Principal, body: s.CourseIn) -> s.CourseAdminOut:
    role = db.scalar(select(RoleProfile).where(RoleProfile.key == body.role_profile))
    if role is None:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Unknown role profile",
            "Run the bootstrap command to create the role profiles.",
        )
    course = Course(
        key=_unique_key(db, Course, f"{_slug(body.role_profile, 12)}.{_slug(body.title)}"),
        role_profile_id=role.id,
        title=body.title.strip(),
        description=body.description.strip(),
        final_deliverable=body.final_deliverable.strip(),
    )
    db.add(course)
    db.flush()
    _audit(db, principal, "course.create", course, {"title": course.title})
    return course_tree(db, course.id)


def update_course(
    db: Session, principal: Principal, course_id: uuid.UUID, body: s.CoursePatch
) -> s.CourseAdminOut:
    course = _get(db, Course, course_id, "Course")
    if body.review_status == "approved" and course.review_status != "approved":
        role = db.get(RoleProfile, course.role_profile_id)
        problems = _approval_problems(db, course, role.key if role else "")
        if problems:
            raise ProblemError(
                status.HTTP_409_CONFLICT,
                "The course is not ready to approve",
                "Fix the items below first.",
                errors=[{"message": p} for p in problems],
            )
    for field in ("title", "description", "final_deliverable", "review_status"):
        value = getattr(body, field)
        if value is not None:
            setattr(course, field, value.strip() if isinstance(value, str) else value)
    db.flush()
    if body.review_status is not None:
        _audit(
            db, principal, "course.review_status", course, {"review_status": course.review_status}
        )
    return course_tree(db, course.id)


def delete_course(db: Session, principal: Principal, course_id: uuid.UUID) -> None:
    course = _get(db, Course, course_id, "Course")
    if (
        db.scalar(select(Enrollment.id).where(Enrollment.course_id == course.id).limit(1))
        is not None
    ):
        raise ProblemError(
            status.HTTP_409_CONFLICT,
            "Interns are enrolled in this course",
            "Courses with enrollments cannot be deleted.",
        )
    for module in db.scalars(select(Module).where(Module.course_id == course.id)).all():
        _delete_module_rows(db, module)
    _audit(db, principal, "course.delete", course, {"title": course.title})
    db.delete(course)
    db.flush()


# ---------- Milestones ----------


def create_module(
    db: Session,
    principal: Principal,
    course_id: uuid.UUID,
    body: s.ModuleIn,
    *,
    draft: bool = False,
) -> s.CourseAdminOut:
    """Add a milestone at the end. A draft milestone (trainer or AI created) is not synced to
    interns; it goes live only through approve_module."""
    course = _get(db, Course, course_id, "Course")
    last = db.scalar(select(func.max(Module.position)).where(Module.course_id == course.id)) or 0
    module = Module(
        key=_unique_key(db, Module, f"{course.key}.m{last + 1}"),
        course_id=course.id,
        position=last + 1,
        title=body.title.strip(),
        description=body.description.strip(),
        learning_objective=body.learning_objective.strip(),
        review_status="draft" if draft else "approved",
        created_by=principal.user_id,
    )
    db.add(module)
    db.flush()
    if not draft:
        sync_course(db, course.id)
    return course_tree(db, course.id)


def approve_module(db: Session, principal: Principal, module_id: uuid.UUID) -> s.CourseAdminOut:
    """Admin approval publishes a draft milestone to enrolled interns (open questions 7.1)."""
    module = _get(db, Module, module_id, "Milestone")
    if module.review_status != "approved":
        problems = []
        if not module.description.strip():
            problems.append("The milestone needs a description.")
        if not module.learning_objective.strip():
            problems.append("The milestone needs a learning objective.")
        if (
            db.scalar(select(TaskTemplate.id).where(TaskTemplate.module_id == module.id).limit(1))
            is None
        ):
            problems.append("The milestone needs at least one task.")
        if problems:
            raise ProblemError(
                status.HTTP_409_CONFLICT,
                "The milestone is not ready to approve",
                "Fix the items below first.",
                errors=[{"message": p} for p in problems],
            )
        module.review_status = "approved"
        db.flush()
        _audit(db, principal, "module.approve", module, {"title": module.title})
        sync_course(db, module.course_id)
    return course_tree(db, module.course_id)


def update_module(
    db: Session, principal: Principal, module_id: uuid.UUID, body: s.ModulePatch
) -> s.CourseAdminOut:
    module = _get(db, Module, module_id, "Milestone")
    for field in ("title", "description", "learning_objective"):
        value = getattr(body, field)
        if value is not None:
            setattr(module, field, value.strip())
    db.flush()
    return course_tree(db, module.course_id)


def reorder_modules(
    db: Session, principal: Principal, course_id: uuid.UUID, body: s.ModuleOrderIn
) -> s.CourseAdminOut:
    course = _get(db, Course, course_id, "Course")
    modules = {m.id: m for m in db.scalars(select(Module).where(Module.course_id == course.id))}
    if set(body.module_ids) != set(modules) or len(body.module_ids) != len(modules):
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Send every milestone of the course exactly once"
        )
    # Two passes so the unique (course, position) constraint never sees a duplicate.
    for offset, module_id in enumerate(body.module_ids, start=1):
        modules[module_id].position = -offset
    db.flush()
    for offset, module_id in enumerate(body.module_ids, start=1):
        modules[module_id].position = offset
    db.flush()
    return course_tree(db, course.id)


def _has_submissions(db: Session, task_ids: list[uuid.UUID]) -> bool:
    if not task_ids:
        return False
    return (
        db.scalar(
            select(Submission.id)
            .join(TaskInstance, TaskInstance.id == Submission.task_instance_id)
            .where(TaskInstance.task_template_id.in_(task_ids))
            .limit(1)
        )
        is not None
    )


def _delete_task_rows(db: Session, task: TaskTemplate) -> None:
    db.execute(delete(TaskInstance).where(TaskInstance.task_template_id == task.id))
    task.rubric_version_id = None
    db.flush()
    db.execute(
        delete(RubricVersion).where(
            RubricVersion.rubric_key == task.key, RubricVersion.published.is_(False)
        )
    )
    db.delete(task)


def _delete_module_rows(db: Session, module: Module) -> None:
    tasks = db.scalars(select(TaskTemplate).where(TaskTemplate.module_id == module.id)).all()
    if _has_submissions(db, [t.id for t in tasks]):
        raise ProblemError(
            status.HTTP_409_CONFLICT,
            "Interns have submitted work here",
            "Milestones and tasks with submissions cannot be deleted.",
        )
    for task in tasks:
        _delete_task_rows(db, task)
    db.execute(delete(MilestoneProgress).where(MilestoneProgress.module_id == module.id))
    db.delete(module)
    db.flush()


def delete_module(db: Session, principal: Principal, module_id: uuid.UUID) -> s.CourseAdminOut:
    module = _get(db, Module, module_id, "Milestone")
    course_id = module.course_id
    _delete_module_rows(db, module)
    # Close the gap so positions stay 1..n.
    remaining = db.scalars(
        select(Module).where(Module.course_id == course_id).order_by(Module.position)
    ).all()
    for index, m in enumerate(remaining, start=1):
        m.position = -index
    db.flush()
    for index, m in enumerate(remaining, start=1):
        m.position = index
    db.flush()
    return course_tree(db, course_id)


# ---------- Tasks ----------


def _manifest(items: list[s.DeliverableIn] | None) -> list[dict[str, Any]]:
    if not items:
        return [dict(d) for d in DEFAULT_DELIVERABLES]
    manifest = [d.model_dump(exclude_none=True, exclude_defaults=False) for d in items]
    for d in manifest:
        for empty in ("accept", "sections", "description"):
            if not d.get(empty):
                d.pop(empty, None)
    problems = deliverable_errors(manifest)
    if problems:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The deliverables need attention",
            errors=[{"message": p} for p in problems],
        )
    return manifest


def create_task(
    db: Session, principal: Principal, module_id: uuid.UUID, body: s.TaskIn
) -> s.CourseAdminOut:
    module = _get(db, Module, module_id, "Milestone")
    course = _get(db, Course, module.course_id, "Course")
    task = TaskTemplate(
        key=_unique_key(db, TaskTemplate, f"{course.key}.{_slug(body.title)}"),
        module_id=module.id,
        title=body.title.strip(),
        task_type=TaskType(body.task_type),
        depth=TaskDepth(body.depth),
        description=body.description.strip(),
        learning_objective=body.learning_objective.strip(),
        submits=body.submits.strip(),
        evaluated_on=body.evaluated_on.strip(),
        requires_review=body.requires_review,
        deliverables=_manifest(body.deliverables),
        starter_files=[],
    )
    db.add(task)
    db.flush()
    sync_course(db, course.id)
    return course_tree(db, course.id)


def update_task(
    db: Session, principal: Principal, task_id: uuid.UUID, body: s.TaskPatch
) -> s.CourseAdminOut:
    task = _get(db, TaskTemplate, task_id, "Task")
    module = _get(db, Module, task.module_id, "Milestone")
    for field in ("title", "description", "learning_objective", "submits", "evaluated_on"):
        value = getattr(body, field)
        if value is not None:
            setattr(task, field, value.strip())
    if body.task_type is not None:
        task.task_type = TaskType(body.task_type)
    if body.depth is not None:
        task.depth = TaskDepth(body.depth)
    if body.requires_review is not None:
        task.requires_review = body.requires_review
    if body.deliverables is not None:
        task.deliverables = _manifest(body.deliverables)
    db.flush()
    return course_tree(db, module.course_id)


def delete_task(db: Session, principal: Principal, task_id: uuid.UUID) -> s.CourseAdminOut:
    task = _get(db, TaskTemplate, task_id, "Task")
    module = _get(db, Module, task.module_id, "Milestone")
    if _has_submissions(db, [task.id]):
        raise ProblemError(
            status.HTTP_409_CONFLICT,
            "Interns have submitted work for this task",
            "Tasks with submissions cannot be deleted.",
        )
    _delete_task_rows(db, task)
    db.flush()
    return course_tree(db, module.course_id)


# ---------- Rubrics ----------


def _rubric_content(
    task: TaskTemplate, role_key: str, version: int, body: s.RubricDraftIn
) -> dict[str, Any]:
    criteria = []
    for c in body.criteria:
        item: dict[str, Any] = {
            "id": c.id,
            "title": c.title.strip(),
            "weight": c.weight,
            "levels": {k: v.strip() for k, v in c.levels.items() if v.strip()},
            "correction_template": c.correction_template.strip(),
        }
        if c.mandatory_min_level is not None:
            item["mandatory_min_level"] = c.mandatory_min_level
        if c.bound_checks:
            item["bound_checks"] = c.bound_checks
        criteria.append(item)
    return {
        "rubric_id": task.key,
        "version": version,
        "role_profile": role_key,
        "pass_threshold": body.pass_threshold,
        "scale": {"min": 0, "max": 4},
        "criteria": criteria,
        "checkers": body.checkers,
    }


def _role_key_for(db: Session, task: TaskTemplate) -> str:
    module = _get(db, Module, task.module_id, "Milestone")
    course = _get(db, Course, module.course_id, "Course")
    role = db.get(RoleProfile, course.role_profile_id)
    return role.key if role else ""


def save_rubric_draft(
    db: Session, principal: Principal, task_id: uuid.UUID, body: s.RubricDraftIn
) -> s.CourseAdminOut:
    task = _get(db, TaskTemplate, task_id, "Task")
    role_key = _role_key_for(db, task)
    allowed = set(checker_registry().get(role_key, []))
    unknown = sorted(set(body.checkers) - allowed)
    if unknown:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Unknown checkers for this role",
            f"Not registered for {role_key}: {', '.join(unknown)}.",
        )
    draft = _draft_for(db, task)
    if draft is None:
        last = (
            db.scalar(
                select(func.max(RubricVersion.version)).where(RubricVersion.rubric_key == task.key)
            )
            or 0
        )
        content = _rubric_content(task, role_key, last + 1, body)
        draft = RubricVersion(
            rubric_key=task.key,
            version=last + 1,
            content=content,
            content_hash=rubric_hash({**content, "_draft": True}),
            published=False,
        )
        db.add(draft)
    else:
        content = _rubric_content(task, role_key, draft.version, body)
        draft.content = content
        draft.content_hash = rubric_hash({**content, "_draft": True})
    db.flush()
    module = _get(db, Module, task.module_id, "Milestone")
    return course_tree(db, module.course_id)


def publish_rubric(db: Session, principal: Principal, task_id: uuid.UUID) -> s.CourseAdminOut:
    task = _get(db, TaskTemplate, task_id, "Task")
    draft = _draft_for(db, task)
    if draft is None:
        raise ProblemError(status.HTTP_409_CONFLICT, "There is no draft rubric to publish")
    report = validate_rubric(draft.content)
    if not report.ok:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The rubric is not ready to publish",
            "Fix the items below first.",
            errors=[{"message": e} for e in report.errors],
        )
    draft.content_hash = rubric_hash(draft.content)
    if (
        db.scalar(
            select(RubricVersion.id).where(
                RubricVersion.content_hash == draft.content_hash, RubricVersion.id != draft.id
            )
        )
        is not None
    ):
        raise ProblemError(
            status.HTTP_409_CONFLICT, "An identical rubric version is already published"
        )
    draft.published = True  # the DB trigger freezes it from here on
    task.rubric_version_id = draft.id
    db.flush()
    _audit(
        db,
        principal,
        "rubric.publish",
        draft,
        {
            "rubric_key": draft.rubric_key,
            "version": draft.version,
            "content_hash": draft.content_hash,
        },
    )
    module = _get(db, Module, task.module_id, "Milestone")
    return course_tree(db, module.course_id)
