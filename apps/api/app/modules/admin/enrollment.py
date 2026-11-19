"""Keep enrollments in step with their course content.

Called after an intern is enrolled and after milestones or tasks are added to a course.
Idempotent: only missing milestone progress and task instances are created; existing progress
and task status are never changed here (approval and unlocking own those, Phase 5).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Module, TaskTemplate
from app.modules.delivery.models import Enrollment, TaskInstance, TaskInstanceStatus
from app.modules.progression.models import MilestoneProgress


def sync_enrollment(db: Session, enrollment: Enrollment) -> int:
    """Create missing progress and task instances. Returns the number of rows created."""
    created = 0
    modules = db.scalars(
        select(Module)
        .where(Module.course_id == enrollment.course_id, Module.review_status == "approved")
        .order_by(Module.position)
    ).all()
    progress = {
        p.module_id: p
        for p in db.scalars(
            select(MilestoneProgress).where(MilestoneProgress.enrollment_id == enrollment.id)
        )
    }
    instances = set(
        db.scalars(
            select(TaskInstance.task_template_id).where(TaskInstance.enrollment_id == enrollment.id)
        )
    )

    for index, module in enumerate(modules):
        row = progress.get(module.id)
        if row is None:
            # The first milestone opens straight away; later ones open on approval of the previous one.
            row = MilestoneProgress(
                enrollment_id=enrollment.id,
                module_id=module.id,
                status="unlocked" if index == 0 else "locked",
            )
            db.add(row)
            created += 1
        task_status = (
            TaskInstanceStatus.unlocked
            if row.status in {"unlocked", "complete"}
            else TaskInstanceStatus.locked
        )
        for task_id in db.scalars(
            select(TaskTemplate.id).where(TaskTemplate.module_id == module.id)
        ):
            if task_id not in instances:
                db.add(
                    TaskInstance(
                        enrollment_id=enrollment.id, task_template_id=task_id, status=task_status
                    )
                )
                created += 1
    db.flush()
    return created


def sync_course(db: Session, course_id: uuid.UUID) -> int:
    total = 0
    for enrollment in db.scalars(select(Enrollment).where(Enrollment.course_id == course_id)):
        total += sync_enrollment(db, enrollment)
    return total
