"""Intern dashboard endpoint (Architecture 14)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.identity.deps import Principal, get_scoped_db, require_permission
from app.modules.identity.permissions import Permission, has_any
from app.modules.progression import service
from app.modules.progression.schemas import InternDashboardOut

router = APIRouter(tags=["intern"])

_READ_OTHERS = (
    Permission.SUBMISSION_READ_ASSIGNED,
    Permission.SUBMISSION_READ_ALL,
    Permission.COHORT_OVERVIEW,
)
_can_view = require_permission(Permission.SUBMISSION_READ_OWN, *_READ_OTHERS)


@router.get("/interns/{intern_id}/dashboard", response_model=InternDashboardOut)
def intern_dashboard(
    intern_id: uuid.UUID,
    principal: Principal = Depends(_can_view),
    db: Session = Depends(get_scoped_db),
) -> InternDashboardOut:
    is_self = intern_id == principal.user_id
    if not is_self and not has_any(principal.roles, *_READ_OTHERS):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intern not found")

    result = service.intern_dashboard(db, intern_id)
    # RLS hides enrollments outside the caller's scope. With none visible, someone else's
    # dashboard is reported as not found rather than as an empty page (no existence leak).
    if result is None or (not is_self and not result.enrollments):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intern not found")
    return result
