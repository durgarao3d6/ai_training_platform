"""Submission endpoints (Architecture 14). Human review required (second engineer)."""

import uuid
from collections.abc import Iterator
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core import storage
from app.core.config import Settings, get_settings
from app.core.errors import ProblemError
from app.modules.identity.deps import Principal, get_scoped_db, require_permission
from app.modules.identity.permissions import Permission
from app.modules.submissions import service
from app.modules.submissions.schemas import (
    SubmissionIn,
    SubmissionOut,
    SubmissionSummaryOut,
    UploadSignIn,
    UploadSignOut,
)

router = APIRouter(tags=["submissions"])

_can_submit = require_permission(Permission.SUBMISSION_CREATE_OWN)
_can_view = require_permission(
    Permission.SUBMISSION_READ_OWN,
    Permission.SUBMISSION_READ_ASSIGNED,
    Permission.SUBMISSION_READ_ALL,
)

IdempotencyKey = Header(default=None, alias="Idempotency-Key", max_length=100)


@router.post("/uploads/sign", response_model=UploadSignOut)
def sign_upload(
    body: UploadSignIn,
    principal: Principal = Depends(_can_submit),
    db: Session = Depends(get_scoped_db),
    settings: Settings = Depends(get_settings),
) -> UploadSignOut:
    return service.sign_upload(db, principal, body, settings)


def _respond(response: Response, result: tuple[SubmissionOut, bool]) -> SubmissionOut:
    submission, created = result
    # 202: accepted for evaluation. A replayed Idempotency-Key returns the original with 200.
    response.status_code = status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
    return submission


@router.post(
    "/task-instances/{task_instance_id}/submissions",
    response_model=SubmissionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_submission(
    task_instance_id: uuid.UUID,
    body: SubmissionIn,
    response: Response,
    idempotency_key: str | None = IdempotencyKey,
    principal: Principal = Depends(_can_submit),
    db: Session = Depends(get_scoped_db),
    settings: Settings = Depends(get_settings),
) -> SubmissionOut:
    return _respond(
        response,
        service.create_submission(db, principal, task_instance_id, body, idempotency_key, settings),
    )


@router.post(
    "/submissions/{submission_id}/resubmit",
    response_model=SubmissionOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def resubmit(
    submission_id: uuid.UUID,
    body: SubmissionIn,
    response: Response,
    idempotency_key: str | None = IdempotencyKey,
    principal: Principal = Depends(_can_submit),
    db: Session = Depends(get_scoped_db),
    settings: Settings = Depends(get_settings),
) -> SubmissionOut:
    """A new attempt on the same task. The earlier attempt is never changed."""
    task_instance_id = service.task_instance_of(db, submission_id)
    return _respond(
        response,
        service.create_submission(db, principal, task_instance_id, body, idempotency_key, settings),
    )


@router.get(
    "/task-instances/{task_instance_id}/submissions",
    response_model=list[SubmissionSummaryOut],
    dependencies=[Depends(_can_view)],
)
def list_submissions(
    task_instance_id: uuid.UUID, db: Session = Depends(get_scoped_db)
) -> list[SubmissionSummaryOut]:
    return service.list_submissions(db, task_instance_id)


@router.get(
    "/submissions/{submission_id}", response_model=SubmissionOut, dependencies=[Depends(_can_view)]
)
def get_submission(submission_id: uuid.UUID, db: Session = Depends(get_scoped_db)) -> SubmissionOut:
    return service.get_submission(db, submission_id)


@router.get("/artifacts/{artifact_id}/download", dependencies=[Depends(_can_view)])
def download_artifact(
    artifact_id: uuid.UUID, db: Session = Depends(get_scoped_db)
) -> StreamingResponse:
    """Streams a submitted file. Always an attachment and never sniffed, so submitted
    content can never run in the platform's origin."""
    artifact = service.get_file_artifact(db, artifact_id)
    try:
        body = storage.stream(artifact.storage_key or "")
        first = next(body, b"")
    except storage.ObjectMissing as exc:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "File not found") from exc

    def chunks() -> Iterator[bytes]:
        yield first
        yield from body

    name = artifact.filename or "file"
    return StreamingResponse(
        chunks(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
