"""Cohorts, enrollments and user accounts (FR-HR-01, FR-IAM).

- HR and admin create cohorts and enroll interns. Enrolling creates the intern's milestone
  progress and task instances from the course's current content.
- HR may create intern accounts only; admin may create any role. Every account creation is
  written to the audit log (Architecture 13.3).
"""

import uuid

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ProblemError
from app.modules.admin import schemas as s
from app.modules.admin.enrollment import sync_enrollment
from app.modules.audit.models import AuditLog
from app.modules.catalog.models import Course, Module
from app.modules.delivery.models import Cohort, Enrollment
from app.modules.identity.deps import Principal
from app.modules.identity.models import Role, RoleAssignment, User
from app.modules.identity.permissions import Permission, has_any
from app.modules.identity.security import hash_password
from app.modules.progression.models import MilestoneProgress


def _roles_of(db: Session, user_id: uuid.UUID) -> list[str]:
    return sorted(
        r.value
        for r in db.scalars(select(RoleAssignment.role).where(RoleAssignment.user_id == user_id))
    )


def _require_role(db: Session, user_id: uuid.UUID, role: Role, what: str) -> User:
    user = db.get(User, user_id)
    if user is None or role.value not in _roles_of(db, user_id):
        raise ProblemError(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Choose a {what}")
    return user


def _cohort_out(db: Session, cohort: Cohort) -> s.CohortOut:
    trainer = db.get(User, cohort.trainer_id) if cohort.trainer_id else None
    return s.CohortOut(
        id=cohort.id,
        name=cohort.name,
        starts_on=cohort.starts_on,
        trainer_id=cohort.trainer_id,
        trainer_name=trainer.full_name if trainer else None,
        enrollment_count=db.scalar(
            select(func.count()).select_from(Enrollment).where(Enrollment.cohort_id == cohort.id)
        )
        or 0,
    )


def list_cohorts(db: Session) -> list[s.CohortOut]:
    return [
        _cohort_out(db, c) for c in db.scalars(select(Cohort).order_by(Cohort.created_at.desc()))
    ]


def cohort_detail(db: Session, cohort_id: uuid.UUID) -> s.CohortDetailOut:
    cohort = db.get(Cohort, cohort_id)
    if cohort is None:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Cohort not found")
    enrollments = []
    for e, user, course in db.execute(
        select(Enrollment, User, Course)
        .join(User, User.id == Enrollment.user_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Enrollment.cohort_id == cohort.id)
        .order_by(User.full_name)
    ):
        total = (
            db.scalar(
                select(func.count())
                .select_from(Module)
                .where(Module.course_id == course.id, Module.review_status == "approved")
            )
            or 0
        )
        complete = (
            db.scalar(
                select(func.count())
                .select_from(MilestoneProgress)
                .where(
                    MilestoneProgress.enrollment_id == e.id, MilestoneProgress.status == "complete"
                )
            )
            or 0
        )
        enrollments.append(
            s.EnrollmentOut(
                id=e.id,
                user_id=user.id,
                intern_name=user.full_name,
                intern_email=user.email,
                course_id=course.id,
                course_title=course.title,
                milestones_complete=complete,
                milestones_total=total,
            )
        )
    return s.CohortDetailOut(**_cohort_out(db, cohort).model_dump(), enrollments=enrollments)


def create_cohort(db: Session, principal: Principal, body: s.CohortIn) -> s.CohortDetailOut:
    if body.trainer_id is not None:
        _require_role(db, body.trainer_id, Role.trainer, "trainer")
    cohort = Cohort(name=body.name.strip(), starts_on=body.starts_on, trainer_id=body.trainer_id)
    db.add(cohort)
    db.flush()
    db.add(
        AuditLog(
            actor_id=principal.user_id,
            action="cohort.create",
            subject_type="cohort",
            subject_id=cohort.id,
            after={"name": cohort.name},
        )
    )
    return cohort_detail(db, cohort.id)


def update_cohort(
    db: Session, principal: Principal, cohort_id: uuid.UUID, body: s.CohortPatch
) -> s.CohortDetailOut:
    cohort = db.get(Cohort, cohort_id)
    if cohort is None:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Cohort not found")
    if body.name is not None:
        cohort.name = body.name.strip()
    if "starts_on" in body.model_fields_set:
        cohort.starts_on = body.starts_on
    if "trainer_id" in body.model_fields_set:
        if body.trainer_id is not None:
            _require_role(db, body.trainer_id, Role.trainer, "trainer")
        cohort.trainer_id = body.trainer_id
    db.flush()
    return cohort_detail(db, cohort.id)


def enroll(
    db: Session, principal: Principal, cohort_id: uuid.UUID, body: s.EnrollmentIn
) -> s.CohortDetailOut:
    cohort = db.get(Cohort, cohort_id)
    if cohort is None:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Cohort not found")
    _require_role(db, body.user_id, Role.intern, "intern")
    if db.get(Course, body.course_id) is None:
        raise ProblemError(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a course")
    if (
        db.scalar(
            select(Enrollment.id).where(
                Enrollment.user_id == body.user_id, Enrollment.course_id == body.course_id
            )
        )
        is not None
    ):
        raise ProblemError(
            status.HTTP_409_CONFLICT, "This intern is already enrolled in that course"
        )
    enrollment = Enrollment(user_id=body.user_id, cohort_id=cohort.id, course_id=body.course_id)
    db.add(enrollment)
    db.flush()
    sync_enrollment(db, enrollment)
    return cohort_detail(db, cohort.id)


# ---------- Users ----------


def list_users(db: Session, role: str | None) -> list[s.UserOut]:
    query = select(User).order_by(User.full_name)
    if role:
        query = query.join(RoleAssignment, RoleAssignment.user_id == User.id).where(
            RoleAssignment.role == Role(role)
        )
    return [
        s.UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            roles=_roles_of(db, u.id),
            created_at=u.created_at,
        )
        for u in db.scalars(query)
    ]


def create_user(db: Session, principal: Principal, body: s.UserIn) -> s.UserOut:
    if body.role != "intern" and not has_any(principal.roles, Permission.USERS_MANAGE_ALL):
        raise ProblemError(status.HTTP_403_FORBIDDEN, "You can create intern accounts only")
    email = body.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ProblemError(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(
        email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password)
    )
    db.add(user)
    db.flush()
    db.add(RoleAssignment(user_id=user.id, role=Role(body.role)))
    db.add(
        AuditLog(
            actor_id=principal.user_id,
            action="user.create",
            subject_type="user",
            subject_id=user.id,
            after={"email": email, "role": body.role},
        )
    )
    db.flush()
    return s.UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=[body.role],
        created_at=user.created_at,
    )
