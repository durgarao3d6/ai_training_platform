"""Assigned trainer reviews and progression (FR-REV-01, FR-REV-03, FR-PRG-01)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import ProblemError
from app.modules.audit.models import AuditLog
from app.modules.catalog.models import Module, RubricVersion, TaskTemplate
from app.modules.delivery.models import Cohort, Enrollment, TaskInstance, TaskInstanceStatus
from app.modules.evaluation.models import EvaluationRun, RunState
from app.modules.identity.deps import Principal
from app.modules.identity.models import User
from app.modules.progression.models import MilestoneProgress
from app.modules.review.models import Decision, ReviewDecision
from app.modules.review.schemas import ReviewInput, ReviewQueueItem, ReviewResult, ReviewRubric
from app.modules.submissions.models import Submission, SubmissionStatus


def _assigned_work(
    principal: Principal,
) -> Select[tuple[Submission, TaskInstance, TaskTemplate, Enrollment, Cohort]]:
    return (
        select(Submission, TaskInstance, TaskTemplate, Enrollment, Cohort)
        .join(TaskInstance, Submission.task_instance_id == TaskInstance.id)
        .join(TaskTemplate, TaskTemplate.id == TaskInstance.task_template_id)
        .join(Enrollment, Enrollment.id == TaskInstance.enrollment_id)
        .join(Cohort, Cohort.id == Enrollment.cohort_id)
        .where(Cohort.trainer_id == principal.user_id)
    )


def queue(db: Session, principal: Principal) -> list[ReviewQueueItem]:
    latest = (
        select(Submission.task_instance_id, func.max(Submission.attempt_number).label("attempt"))
        .group_by(Submission.task_instance_id)
        .subquery()
    )
    rubric_id = func.coalesce(EvaluationRun.rubric_version_id, TaskTemplate.rubric_version_id)
    rows = db.execute(
        _assigned_work(principal)
        .join(
            latest,
            (latest.c.task_instance_id == TaskInstance.id)
            & (latest.c.attempt == Submission.attempt_number),
        )
        .join(User, User.id == Enrollment.user_id)
        .outerjoin(
            EvaluationRun,
            (EvaluationRun.submission_id == Submission.id)
            & (EvaluationRun.state == RunState.human_review),
        )
        .join(RubricVersion, (RubricVersion.id == rubric_id) & RubricVersion.published)
        .add_columns(User.full_name, RubricVersion.id)
        .where(
            TaskInstance.status.in_(
                [TaskInstanceStatus.in_progress, TaskInstanceStatus.review_pending]
            ),
            Submission.status == SubmissionStatus.received,
        )
        .order_by(Submission.created_at, Submission.id)
    )
    return [
        ReviewQueueItem(
            submission_id=submission.id,
            attempt_number=submission.attempt_number,
            submitted_at=submission.created_at,
            intern_name=intern_name,
            task_title=template.title,
            cohort_name=cohort.name,
            rubric_version_id=version_id,
        )
        for submission, _, template, _, cohort, intern_name, version_id in rows
    ]


def _review_run(db: Session, submission_id: uuid.UUID) -> EvaluationRun | None:
    return db.scalar(
        select(EvaluationRun).where(
            EvaluationRun.submission_id == submission_id,
            EvaluationRun.state == RunState.human_review,
        )
    )


def _published_rubric(
    db: Session, template: TaskTemplate, run: EvaluationRun | None
) -> RubricVersion:
    rubric_id = run.rubric_version_id if run else template.rubric_version_id
    rubric = db.get(RubricVersion, rubric_id) if rubric_id else None
    if rubric is None or not rubric.published:
        raise ProblemError(409, "Publish a rubric before reviewing this attempt")
    return rubric


def rubric_for_review(db: Session, principal: Principal, submission_id: uuid.UUID) -> ReviewRubric:
    row = db.execute(_assigned_work(principal).where(Submission.id == submission_id)).one_or_none()
    if row is None:
        raise ProblemError(404, "Submission not found")
    _, _, template, _, _ = row
    run = db.scalar(
        select(EvaluationRun)
        .where(EvaluationRun.submission_id == submission_id)
        .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
        .limit(1)
    )
    rubric = _published_rubric(db, template, run)
    return ReviewRubric(id=rubric.id, version=rubric.version, content=rubric.content)


def _advance(db: Session, enrollment: Enrollment, module: Module) -> None:
    unfinished = db.scalar(
        select(TaskInstance.id)
        .join(TaskTemplate, TaskTemplate.id == TaskInstance.task_template_id)
        .where(
            TaskInstance.enrollment_id == enrollment.id,
            TaskTemplate.module_id == module.id,
            TaskInstance.status != TaskInstanceStatus.complete,
        )
        .limit(1)
    )
    if unfinished is not None:
        return
    progress = db.scalar(
        select(MilestoneProgress).where(
            MilestoneProgress.enrollment_id == enrollment.id,
            MilestoneProgress.module_id == module.id,
        )
    )
    if progress is None:
        raise ProblemError(409, "Milestone progress is missing")
    progress.status = "complete"
    progress.completed_at = datetime.now(UTC)
    following = db.scalar(
        select(MilestoneProgress)
        .join(Module, Module.id == MilestoneProgress.module_id)
        .where(
            MilestoneProgress.enrollment_id == enrollment.id,
            Module.course_id == enrollment.course_id,
            Module.position > module.position,
            Module.review_status == "approved",
        )
        .order_by(Module.position)
        .limit(1)
    )
    if following is None or following.status != "locked":
        return
    following.status = "unlocked"
    for task in db.scalars(
        select(TaskInstance)
        .join(TaskTemplate, TaskTemplate.id == TaskInstance.task_template_id)
        .where(
            TaskInstance.enrollment_id == enrollment.id,
            TaskTemplate.module_id == following.module_id,
            TaskInstance.status == TaskInstanceStatus.locked,
        )
    ):
        task.status = TaskInstanceStatus.unlocked


def decide(
    db: Session, principal: Principal, submission_id: uuid.UUID, body: ReviewInput
) -> ReviewResult:
    reason = body.reason.strip()
    if body.decision == "request_revision" and not reason:
        raise ProblemError(422, "Explain what the intern should revise")
    row = db.execute(
        _assigned_work(principal)
        .where(Submission.id == submission_id)
        .with_for_update(of=[Cohort.id, Enrollment.id])
    ).one_or_none()
    if row is None:
        raise ProblemError(404, "Submission not found")
    submission, instance, template, enrollment, _ = row
    # Serialize reviews across tasks in the same enrollment, then contend with submission writes.
    db.refresh(instance, with_for_update=True)
    db.refresh(submission)
    latest = db.scalar(
        select(func.max(Submission.attempt_number)).where(
            Submission.task_instance_id == instance.id
        )
    )
    if (
        submission.attempt_number != latest
        or submission.status != SubmissionStatus.received
        or instance.status
        not in {TaskInstanceStatus.in_progress, TaskInstanceStatus.review_pending}
    ):
        raise ProblemError(409, "This attempt is no longer waiting for a decision")

    run = _review_run(db, submission_id)
    rubric = _published_rubric(db, template, run)
    if rubric.id != body.rubric_version_id:
        raise ProblemError(409, "The rubric changed. Reload the attempt before reviewing it.")
    if run is None:
        # Older attempts had no evaluation row. Use the published rubric presented for review.
        run = EvaluationRun(submission_id=submission.id, rubric_version_id=rubric.id)
        db.add(run)
        db.flush()
    approved = body.decision == "approve"
    run.state = RunState.approved if approved else RunState.revision_required
    submission.status = SubmissionStatus.evaluated
    instance.status = (
        TaskInstanceStatus.complete if approved else TaskInstanceStatus.needs_another_pass
    )
    decision = ReviewDecision(
        run_id=run.id,
        reviewer_id=principal.user_id,
        decision=Decision(body.decision),
        reason=reason,
    )
    db.add(decision)
    db.add(
        AuditLog(
            actor_id=principal.user_id,
            action="submission.review",
            subject_type="submission",
            subject_id=submission.id,
            reason=reason,
            after={"decision": body.decision, "rubric_version_id": str(rubric.id)},
        )
    )
    if approved:
        module = db.get(Module, template.module_id)
        assert module is not None
        _advance(db, enrollment, module)
    db.flush()
    return ReviewResult(
        decision=body.decision,
        reason=reason,
        decided_at=decision.created_at,
        rubric_version_id=rubric.id,
    )
