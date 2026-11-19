"""Submissions service (tasks 4.1, 4.2). Human review required (second engineer).

Rules:
- Only the intern who owns a task instance can sign uploads or submit for it.
- Every attempt is a new, immutable submission (DB triggers enforce it); attempt numbers are
  assigned under a row lock on the task instance.
- An Idempotency-Key replays the original submission instead of creating a new attempt.
- Validation here checks each artifact against the task's deliverable manifest: known
  deliverable, allowed kind, file type and size from the stored object, non-empty content,
  reachable public links. Completeness of the whole bundle is an evaluation stage (Phase 4).
- The submission row, its artifacts and the outbox event are written in one transaction.
"""

import re
import uuid
from collections import Counter
from pathlib import PurePosixPath
from typing import Any

import structlog
from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import storage
from app.core.config import Settings
from app.core.errors import ProblemError
from app.core.links import check_link
from app.db.outbox import enqueue
from app.modules.catalog import service as catalog
from app.modules.catalog.models import RubricVersion, TaskTemplate
from app.modules.catalog.schemas import kinds_of
from app.modules.delivery.models import Enrollment, TaskInstance, TaskInstanceStatus
from app.modules.evaluation.models import EvaluationRun, RunState
from app.modules.identity.deps import Principal
from app.modules.review.models import Decision, ReviewDecision
from app.modules.review.schemas import ReviewResult
from app.modules.submissions.models import Artifact, ArtifactKind, Submission, SubmissionStatus
from app.modules.submissions.schemas import (
    ArtifactIn,
    ArtifactOut,
    SubmissionIn,
    SubmissionOut,
    SubmissionSummaryOut,
    UploadSignIn,
    UploadSignOut,
    artifact_problem,
)

OPEN_STATUSES = {
    TaskInstanceStatus.unlocked,
    TaskInstanceStatus.in_progress,
    TaskInstanceStatus.needs_another_pass,
}
_log = structlog.get_logger(__name__)
DEFAULT_MAX = {"file": 20, "link": 10, "text": 1}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _not_found() -> ProblemError:
    return ProblemError(status.HTTP_404_NOT_FOUND, "Task not found")


def _owned_instance(
    db: Session, principal: Principal, task_instance_id: uuid.UUID, *, lock: bool = False
) -> TaskInstance:
    """The task instance, if it belongs to the caller. Same 404 otherwise (no existence leak)."""
    query = select(TaskInstance).where(TaskInstance.id == task_instance_id)
    instance = db.scalar(query.with_for_update() if lock else query)
    if instance is None:
        raise _not_found()
    enrollment = db.get(Enrollment, instance.enrollment_id)
    if enrollment is None or enrollment.user_id != principal.user_id:
        raise _not_found()
    return instance


def _require_open(instance: TaskInstance) -> None:
    if instance.status not in OPEN_STATUSES:
        reason = {
            TaskInstanceStatus.locked: "This task is still locked.",
            TaskInstanceStatus.review_pending: "Your last attempt is waiting for trainer review.",
            TaskInstanceStatus.complete: "This task is already approved.",
        }.get(instance.status, "This task is not open for submissions.")
        raise ProblemError(status.HTTP_409_CONFLICT, "Submissions are closed for this task", reason)


def _manifest(db: Session, instance: TaskInstance) -> dict[str, dict[str, Any]]:
    return {d["id"]: d for d in catalog.get_deliverables(db, instance.task_template_id)}


def _extension(name: str) -> str:
    return PurePosixPath(name).suffix.lower()


def _key_prefix(instance: TaskInstance) -> str:
    return f"submissions/{instance.id}/"


def sign_upload(
    db: Session, principal: Principal, body: UploadSignIn, settings: Settings
) -> UploadSignOut:
    instance = _owned_instance(db, principal, body.task_instance_id)
    _require_open(instance)
    deliverable = _manifest(db, instance).get(body.deliverable_id)
    if deliverable is None or "file" not in kinds_of(deliverable):
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "This deliverable does not take files"
        )
    accept = deliverable.get("accept", [])
    if accept and _extension(body.filename) not in accept:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This file type is not accepted",
            f"Accepted types: {', '.join(accept)}.",
        )
    if body.size_bytes > settings.max_upload_bytes:
        raise ProblemError(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "The file is too large",
            f"The limit is {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )

    stem = _SAFE_NAME.sub("_", PurePosixPath(body.filename).stem)[:80] or "file"
    key = f"{_key_prefix(instance)}{uuid.uuid4()}/{stem}{_extension(body.filename)}"
    signed = storage.presign_upload(
        key, body.content_type, settings.max_upload_bytes, settings.upload_url_ttl_seconds
    )
    return UploadSignOut(
        upload_key=key,
        url=signed["url"],
        fields=signed["fields"],
        expires_in=settings.upload_url_ttl_seconds,
        max_bytes=settings.max_upload_bytes,
    )


def _validate(
    instance: TaskInstance,
    manifest: dict[str, dict[str, Any]],
    items: list[ArtifactIn],
    settings: Settings,
    snapshot_keys: list[str],
) -> list[Artifact]:
    """Build artifacts or raise a 422 listing every problem."""
    problems: list[dict[str, Any]] = []
    counts = Counter((a.deliverable_id, a.kind) for a in items)
    per_deliverable = Counter(a.deliverable_id for a in items)

    for deliverable_id, n in per_deliverable.items():
        d = manifest.get(deliverable_id)
        if d is not None and d.get("max_count") and n > d["max_count"]:
            problems.append(
                artifact_problem(deliverable_id, f"Hand in at most {d['max_count']} items here.")
            )
    for (deliverable_id, kind), n in counts.items():
        d = manifest.get(deliverable_id)
        if d is not None and not d.get("max_count") and n > DEFAULT_MAX[kind]:
            problems.append(
                artifact_problem(deliverable_id, f"Too many {kind} items for this deliverable.")
            )

    artifacts: list[Artifact] = []
    pending_links: list[tuple[ArtifactIn, Artifact]] = []
    for item in items:
        d = manifest.get(item.deliverable_id)
        if d is None:
            problems.append(
                artifact_problem(item.deliverable_id, "This task has no such deliverable.")
            )
            continue
        if item.kind not in kinds_of(d):
            problems.append(
                artifact_problem(
                    item.deliverable_id, f"This deliverable does not take a {item.kind}."
                )
            )
            continue

        if item.kind == "file":
            key = item.upload_key or ""
            if not key.startswith(_key_prefix(instance)):
                problems.append(
                    artifact_problem(
                        item.deliverable_id, "This upload does not belong to this task."
                    )
                )
                continue
            accept = d.get("accept", [])
            if accept and _extension(key) not in accept:
                problems.append(
                    artifact_problem(item.deliverable_id, f"Accepted types: {', '.join(accept)}.")
                )
                continue
            snapshot_key = f"submitted-artifacts/{instance.id}/{uuid.uuid4()}"
            snapshot_keys.append(snapshot_key)
            try:
                stored = storage.snapshot(key, snapshot_key)
            except storage.ObjectMissing:
                problems.append(
                    artifact_problem(
                        item.deliverable_id, "The upload did not finish. Upload the file again."
                    )
                )
                continue
            if stored.size_bytes == 0:
                problems.append(artifact_problem(item.deliverable_id, "The file is empty."))
            elif stored.size_bytes > settings.max_upload_bytes:
                problems.append(artifact_problem(item.deliverable_id, "The file is too large."))
            else:
                artifacts.append(
                    Artifact(
                        deliverable_id=item.deliverable_id,
                        kind=ArtifactKind.file,
                        storage_key=stored.key,
                        filename=PurePosixPath(key).name,
                        content_type=stored.content_type,
                        size_bytes=stored.size_bytes,
                        sha256=stored.sha256,
                    )
                )

        elif item.kind == "text":
            text = (item.text or "").strip()
            if not text:
                problems.append(artifact_problem(item.deliverable_id, "The text is empty."))
            elif len(text) > settings.max_text_chars:
                problems.append(
                    artifact_problem(
                        item.deliverable_id,
                        f"Keep the text under {settings.max_text_chars} characters.",
                    )
                )
            elif "\x00" in text:
                problems.append(
                    artifact_problem(
                        item.deliverable_id, "The text contains characters we cannot store."
                    )
                )
            else:
                artifacts.append(
                    Artifact(
                        deliverable_id=item.deliverable_id,
                        kind=ArtifactKind.text,
                        text_content=text,
                    )
                )

        else:  # link: checked last, after every cheap check, because it uses the network
            artifact = Artifact(
                deliverable_id=item.deliverable_id,
                kind=ArtifactKind.link,
                url=(item.url or "").strip(),
            )
            pending_links.append((item, artifact))

    if not problems:
        for item, artifact in pending_links:
            result = check_link(artifact.url or "", settings.link_check_timeout_seconds)
            if result.ok:
                artifacts.append(artifact)
            else:
                problems.append(artifact_problem(item.deliverable_id, result.reason))

    if problems:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Some items need attention",
            "Nothing was submitted. Fix the items below and submit again.",
            errors=problems,
        )
    return artifacts


def _artifact_out(a: Artifact) -> ArtifactOut:
    return ArtifactOut(
        id=a.id,
        deliverable_id=a.deliverable_id,
        kind=a.kind.value,
        filename=a.filename,
        content_type=a.content_type,
        size_bytes=a.size_bytes,
        sha256=a.sha256,
        url=a.url,
        text=a.text_content,
        download_path=f"/api/v1/artifacts/{a.id}/download" if a.kind is ArtifactKind.file else None,
    )


def _submission_out(db: Session, submission: Submission) -> SubmissionOut:
    artifacts = db.scalars(
        select(Artifact)
        .where(Artifact.submission_id == submission.id)
        .order_by(Artifact.deliverable_id, Artifact.created_at)
    ).all()
    run = db.scalar(
        select(EvaluationRun)
        .where(EvaluationRun.submission_id == submission.id)
        .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
        .limit(1)
    )
    review = None
    if run is not None:
        record = db.scalar(
            select(ReviewDecision)
            .where(
                ReviewDecision.run_id == run.id,
                ReviewDecision.decision.in_([Decision.approve, Decision.request_revision]),
            )
            .order_by(ReviewDecision.created_at.desc(), ReviewDecision.id.desc())
            .limit(1)
        )
        if record is not None:
            review = ReviewResult(
                decision="approve" if record.decision == Decision.approve else "request_revision",
                reason=record.reason or "",
                decided_at=record.created_at,
                rubric_version_id=run.rubric_version_id,
            )
    return SubmissionOut(
        id=submission.id,
        task_instance_id=submission.task_instance_id,
        attempt_number=submission.attempt_number,
        status=submission.status.value,
        created_at=submission.created_at,
        artifacts=[_artifact_out(a) for a in artifacts],
        evaluation_id=run.id if run else None,
        review=review,
    )


def create_submission(
    db: Session,
    principal: Principal,
    task_instance_id: uuid.UUID,
    body: SubmissionIn,
    idempotency_key: str | None,
    settings: Settings,
) -> tuple[SubmissionOut, bool]:
    """Returns (submission, created). created is False when an Idempotency-Key replays."""
    instance = _owned_instance(db, principal, task_instance_id, lock=True)

    if idempotency_key:
        existing = db.scalar(
            select(Submission).where(
                Submission.task_instance_id == instance.id,
                Submission.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return _submission_out(db, existing), False

    _require_open(instance)
    snapshot_keys: list[str] = []
    try:
        artifacts = _validate(
            instance, _manifest(db, instance), body.artifacts, settings, snapshot_keys
        )

        last = db.scalar(
            select(func.max(Submission.attempt_number)).where(
                Submission.task_instance_id == instance.id
            )
        )
        submission = Submission(
            task_instance_id=instance.id,
            attempt_number=(last or 0) + 1,
            idempotency_key=idempotency_key,
            status=SubmissionStatus.received,
        )
        db.add(submission)
        db.flush()
        for artifact in artifacts:
            artifact.submission_id = submission.id
            db.add(artifact)
        rubric = db.scalar(
            select(RubricVersion)
            .join(TaskTemplate, TaskTemplate.rubric_version_id == RubricVersion.id)
            .where(TaskTemplate.id == instance.task_template_id, RubricVersion.published)
        )
        if rubric is not None:
            db.add(
                EvaluationRun(
                    submission_id=submission.id,
                    rubric_version_id=rubric.id,
                    state=RunState.human_review,
                )
            )
            instance.status = TaskInstanceStatus.review_pending
        else:
            instance.status = TaskInstanceStatus.in_progress
        enqueue(db, "submission.created", {"submission_id": str(submission.id)})
        db.flush()
        return _submission_out(db, submission), True
    except Exception:
        for key in snapshot_keys:
            try:
                storage.delete(key)
            except Exception:
                _log.warning("submission_snapshot_cleanup_failed", key=key, exc_info=True)
        raise


def task_instance_of(db: Session, submission_id: uuid.UUID) -> uuid.UUID:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Submission not found")
    return submission.task_instance_id


def list_submissions(db: Session, task_instance_id: uuid.UUID) -> list[SubmissionSummaryOut]:
    """RLS limits rows to what the caller may see; an unknown task simply has no rows."""
    if db.get(TaskInstance, task_instance_id) is None:
        raise _not_found()
    rows = db.execute(
        select(Submission, func.count(Artifact.id))
        .outerjoin(Artifact, Artifact.submission_id == Submission.id)
        .where(Submission.task_instance_id == task_instance_id)
        .group_by(Submission.id)
        .order_by(Submission.attempt_number.desc())
    ).all()
    return [
        SubmissionSummaryOut(
            id=s.id,
            attempt_number=s.attempt_number,
            status=s.status.value,
            created_at=s.created_at,
            artifact_count=n,
        )
        for s, n in rows
    ]


def get_submission(db: Session, submission_id: uuid.UUID) -> SubmissionOut:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Submission not found")
    return _submission_out(db, submission)


def get_file_artifact(db: Session, artifact_id: uuid.UUID) -> Artifact:
    artifact = db.get(Artifact, artifact_id)
    if artifact is None or artifact.kind is not ArtifactKind.file or not artifact.storage_key:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "File not found")
    return artifact
