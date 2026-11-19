"""Trainer-only routes. Assignment is checked in the service and by RLS."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.identity.deps import Principal, get_scoped_db, require_permission
from app.modules.identity.permissions import Permission
from app.modules.review import service
from app.modules.review.schemas import ReviewInput, ReviewQueueItem, ReviewResult, ReviewRubric

router = APIRouter(prefix="/trainer", tags=["trainer review"])
_can_review = require_permission(Permission.SUBMISSION_REVIEW)


@router.get("/review-queue")
def review_queue(
    principal: Principal = Depends(_can_review), db: Session = Depends(get_scoped_db)
) -> list[ReviewQueueItem]:
    return service.queue(db, principal)


@router.get("/submissions/{submission_id}/rubric")
def review_rubric(
    submission_id: uuid.UUID,
    principal: Principal = Depends(_can_review),
    db: Session = Depends(get_scoped_db),
) -> ReviewRubric:
    return service.rubric_for_review(db, principal, submission_id)


@router.post("/submissions/{submission_id}/decision")
def record_decision(
    submission_id: uuid.UUID,
    body: ReviewInput,
    principal: Principal = Depends(_can_review),
    db: Session = Depends(get_scoped_db),
) -> ReviewResult:
    return service.decide(db, principal, submission_id, body)
