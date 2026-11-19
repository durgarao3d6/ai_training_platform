"""Progression read model: the intern dashboard (FR-INT-01, FR-INT-02).

Visibility comes from RLS on enrollment, milestone_progress and task_instance.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Course, Module, RoleProfile, TaskTemplate
from app.modules.delivery.models import Cohort, Enrollment, TaskInstance, TaskInstanceStatus
from app.modules.identity.models import User
from app.modules.progression.models import MilestoneProgress
from app.modules.progression.schemas import (
    CurrentTaskOut,
    DashboardTaskOut,
    EnrollmentDashboardOut,
    InternDashboardOut,
    MilestoneStatusOut,
)

# Order in which a task is picked as "current": work waiting on the intern first.
_CURRENT_PRIORITY = [
    TaskInstanceStatus.needs_another_pass,
    TaskInstanceStatus.in_progress,
    TaskInstanceStatus.unlocked,
    TaskInstanceStatus.review_pending,
]


def _reason(status: str, previous_title: str | None) -> str:
    if status == "complete":
        return "Approved by your trainer."
    if status == "unlocked":
        return "Open now."
    if previous_title is None:
        return "Unlocks when your trainer starts the course."
    return f"Unlocks when “{previous_title}” is approved."


def _enrollment_dashboard(db: Session, enrollment: Enrollment) -> EnrollmentDashboardOut:
    course = db.get(Course, enrollment.course_id)
    cohort = db.get(Cohort, enrollment.cohort_id)
    assert course is not None and cohort is not None  # FK guarantees
    role = db.get(RoleProfile, course.role_profile_id)
    trainer = (
        db.get(User, cohort.trainer_id) if cohort.trainer_id else None
    )  # shown on the trainer card

    modules = db.scalars(
        select(Module)
        .where(Module.course_id == course.id, Module.review_status == "approved")
        .order_by(Module.position)
    ).all()
    progress = {
        p.module_id: p.status
        for p in db.scalars(
            select(MilestoneProgress).where(MilestoneProgress.enrollment_id == enrollment.id)
        )
    }
    task_rows = db.execute(
        select(TaskInstance, TaskTemplate)
        .join(TaskTemplate, TaskTemplate.id == TaskInstance.task_template_id)
        .where(TaskInstance.enrollment_id == enrollment.id)
        .order_by(TaskTemplate.title)
    ).all()
    tasks_by_module: dict[uuid.UUID, list[tuple[TaskInstance, TaskTemplate]]] = {}
    for instance, template in task_rows:
        tasks_by_module.setdefault(template.module_id, []).append((instance, template))

    milestones: list[MilestoneStatusOut] = []
    current: CurrentTaskOut | None = None
    best_rank = len(_CURRENT_PRIORITY)
    previous_title: str | None = None

    for module in modules:
        status = progress.get(module.id, "locked")
        tasks = tasks_by_module.get(module.id, [])
        milestones.append(
            MilestoneStatusOut(
                id=module.id,
                key=module.key,
                title=module.title,
                position=module.position,
                status=status,
                reason=_reason(status, previous_title),
                tasks=[
                    DashboardTaskOut(
                        task_instance_id=i.id,
                        task_template_id=t.id,
                        title=t.title,
                        status=i.status.value,
                    )
                    for i, t in tasks
                ],
            )
        )
        for instance, template in tasks:
            if instance.status in _CURRENT_PRIORITY:
                rank = _CURRENT_PRIORITY.index(instance.status)
                if rank < best_rank:  # earliest milestone wins ties, since modules are ordered
                    best_rank = rank
                    current = CurrentTaskOut(
                        task_instance_id=instance.id,
                        title=template.title,
                        milestone_title=module.title,
                        status=instance.status.value,
                    )
        previous_title = module.title

    return EnrollmentDashboardOut(
        enrollment_id=enrollment.id,
        course_id=course.id,
        course_title=course.title,
        role_profile=role.key if role else "",
        cohort_name=cohort.name,
        trainer_name=trainer.full_name if trainer else None,
        milestones=milestones,
        current=current,
    )


def intern_dashboard(db: Session, intern_id: uuid.UUID) -> InternDashboardOut | None:
    user = db.get(User, intern_id)
    if user is None:
        return None
    enrollments = db.scalars(select(Enrollment).where(Enrollment.user_id == intern_id)).all()
    return InternDashboardOut(
        intern_id=user.id,
        full_name=user.full_name,
        enrollments=[_enrollment_dashboard(db, e) for e in enrollments],
    )
