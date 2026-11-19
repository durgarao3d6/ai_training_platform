"""Delivery endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.delivery import service
from app.modules.delivery.schemas import TaskInstanceOut
from app.modules.identity.deps import get_scoped_db, require_permission
from app.modules.identity.permissions import Permission

router = APIRouter(tags=["delivery"])

_can_view_task = require_permission(
    Permission.SUBMISSION_READ_OWN,
    Permission.SUBMISSION_READ_ASSIGNED,
    Permission.SUBMISSION_READ_ALL,
    Permission.COHORT_OVERVIEW,
)


@router.get(
    "/task-instances/{task_instance_id}",
    response_model=TaskInstanceOut,
    dependencies=[Depends(_can_view_task)],
)
def get_task_instance(
    task_instance_id: uuid.UUID, db: Session = Depends(get_scoped_db)
) -> TaskInstanceOut:
    result = service.get_task_instance(db, task_instance_id)
    if result is None:
        # Same answer whether it does not exist or belongs to someone else (no existence leak).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return result
