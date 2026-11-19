"""Delivery service. Row visibility is enforced by RLS: rows the caller may not see do not exist."""

import uuid

from sqlalchemy.orm import Session

from app.modules.catalog import service as catalog
from app.modules.delivery.models import TaskInstance
from app.modules.delivery.schemas import TaskInstanceOut


def get_task_instance(db: Session, task_instance_id: uuid.UUID) -> TaskInstanceOut | None:
    instance = db.get(TaskInstance, task_instance_id)
    if instance is None:
        return None
    task = catalog.get_task_template(db, instance.task_template_id)
    if task is None:
        return None
    return TaskInstanceOut(
        id=instance.id,
        status=instance.status.value,
        enrollment_id=instance.enrollment_id,
        task=task,
    )
