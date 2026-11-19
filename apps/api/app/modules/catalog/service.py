"""Catalog service: the read interface other modules use (never the tables directly)."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Course, Module, RoleProfile, RubricVersion, TaskTemplate
from app.modules.catalog.schemas import (
    CourseOut,
    ModuleOut,
    TaskSummaryOut,
    TaskTemplateOut,
    deliverable_out,
    rubric_out,
)


def list_courses(db: Session, page: int, page_size: int) -> tuple[list[CourseOut], int]:
    total = db.scalar(select(func.count()).select_from(Course)) or 0
    milestone_count = (
        select(func.count())
        .where(Module.course_id == Course.id, Module.review_status == "approved")
        .correlate(Course)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Course, RoleProfile.key, milestone_count)
        .join(RoleProfile, RoleProfile.id == Course.role_profile_id)
        .order_by(Course.title)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        CourseOut(
            id=c.id,
            key=c.key,
            title=c.title,
            description=c.description,
            role_profile=role_key,
            milestone_count=count,
            review_status=c.review_status,
        )
        for c, role_key, count in rows
    ]
    return items, total


def course_exists(db: Session, course_id: uuid.UUID) -> bool:
    return db.get(Course, course_id) is not None


def list_modules(db: Session, course_id: uuid.UUID) -> list[ModuleOut]:
    modules = db.scalars(
        select(Module)
        .where(Module.course_id == course_id, Module.review_status == "approved")
        .order_by(Module.position)
    ).all()
    tasks = db.scalars(
        select(TaskTemplate)
        .where(TaskTemplate.module_id.in_([m.id for m in modules]))
        .order_by(TaskTemplate.title)
    ).all()
    by_module: dict[uuid.UUID, list[TaskSummaryOut]] = {}
    for t in tasks:
        by_module.setdefault(t.module_id, []).append(
            TaskSummaryOut(
                id=t.id, key=t.key, title=t.title, task_type=t.task_type.value, depth=t.depth.value
            )
        )
    return [
        ModuleOut(
            id=m.id,
            key=m.key,
            title=m.title,
            position=m.position,
            description=m.description,
            tasks=by_module.get(m.id, []),
        )
        for m in modules
    ]


def get_task_template(db: Session, task_template_id: uuid.UUID) -> TaskTemplateOut | None:
    task = db.get(TaskTemplate, task_template_id)
    if task is None:
        return None
    rubric = None
    if task.rubric_version_id is not None:
        version = db.get(RubricVersion, task.rubric_version_id)
        if version is not None and version.published:  # interns only ever see published rubrics
            rubric = rubric_out(version.content)
    return TaskTemplateOut(
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
        starter_files=[path.rsplit("/", 1)[-1] for path in task.starter_files],
        deliverables=[deliverable_out(d) for d in task.deliverables],
        rubric=rubric,
    )


def get_deliverables(db: Session, task_template_id: uuid.UUID) -> list[dict[str, Any]]:
    """Raw manifest for the submission and evaluation stages."""
    task = db.get(TaskTemplate, task_template_id)
    return list(task.deliverables) if task is not None else []
