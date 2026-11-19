"""AI-assisted authoring service (open questions section 7).

Rules this module enforces:
- AI output is stored as a proposal on ai_job. Nothing reaches the catalog until a person accepts.
- Accepted milestones are created as draft and stay hidden from interns until an admin approves.
- Accepted components start as draft. Only an admin approves them.
- Material is never overwritten: accepted edits add a new version.
- The model never sets a score and never publishes a rubric.
- Jobs run inside the request for now. The worker and outbox relay are not built yet.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ProblemError
from app.modules.admin import catalog_service as catalog
from app.modules.admin import schemas as admin_s
from app.modules.audit.models import AuditLog
from app.modules.authoring import schemas as s
from app.modules.authoring.models import (
    AiJob,
    AiJobKind,
    AiJobStatus,
    ComponentType,
    CourseComponent,
    CourseMaterial,
)
from app.modules.catalog.models import Course, Module, TaskTemplate
from app.modules.delivery.models import Enrollment
from app.modules.identity.deps import Principal
from app.modules.identity.permissions import Permission, has_any
from app.modules.llm_gateway import service as gateway
from app.modules.progression.models import MilestoneProgress


def require_enabled() -> None:
    if not get_settings().ai_authoring_enabled:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "AI authoring is not enabled")


def is_admin(principal: Principal) -> bool:
    return has_any(principal.roles, Permission.CATALOG_MANAGE)


def _audit(
    db: Session,
    principal: Principal,
    action: str,
    table: str,
    subject_id: uuid.UUID,
    after: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=principal.user_id,
            action=action,
            subject_type=table,
            subject_id=subject_id,
            after=after,
        )
    )


def _get[T](db: Session, model: type[T], id_: uuid.UUID, what: str) -> T:
    row = db.get(model, id_)
    if row is None:
        raise ProblemError(status.HTTP_404_NOT_FOUND, f"{what} not found")
    return row


# ---------- Output mappers ----------


def job_out(job: AiJob) -> s.JobOut:
    return s.JobOut(
        id=job.id,
        kind=job.kind.value,
        status=job.status.value,
        course_id=job.course_id,
        module_id=job.module_id,
        task_id=job.task_id,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
    )


def component_out(c: CourseComponent) -> s.ComponentOut:
    return s.ComponentOut(
        id=c.id,
        module_id=c.module_id,
        task_id=c.task_id,
        type=c.type.value,
        title=c.title,
        payload=c.payload,
        review_status=c.review_status,
        ai_generated=c.ai_generated,
        created_by=c.created_by,
        approved_by=c.approved_by,
        approved_at=c.approved_at,
    )


def material_out(m: CourseMaterial) -> s.MaterialOut:
    return s.MaterialOut(
        id=m.id,
        module_id=m.module_id,
        task_id=m.task_id,
        filename=m.filename,
        version=m.version,
        text=m.extracted_text or "",
        created_at=m.created_at,
    )


def own_job(db: Session, principal: Principal, job_id: uuid.UUID) -> AiJob:
    job = _get(db, AiJob, job_id, "Job")
    if job.requester_id != principal.user_id and not is_admin(principal):
        raise ProblemError(
            status.HTTP_404_NOT_FOUND, "Job not found"
        )  # do not reveal other people's jobs
    return job


def _target(
    db: Session, module_id: uuid.UUID | None, task_id: uuid.UUID | None
) -> tuple[uuid.UUID | None, uuid.UUID | None, dict[str, str]]:
    """Validate that exactly one of module or task is given and return a description of it."""
    if (module_id is None) == (task_id is None):
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose either a milestone or a task"
        )
    if task_id is not None:
        t = _get(db, TaskTemplate, task_id, "Task")
        return (
            None,
            t.id,
            {
                "kind": "task",
                "title": t.title,
                "description": t.description,
                "learning_objective": t.learning_objective,
            },
        )
    assert module_id is not None
    m = _get(db, Module, module_id, "Milestone")
    return (
        m.id,
        None,
        {
            "kind": "module",
            "title": m.title,
            "description": m.description,
            "learning_objective": m.learning_objective,
        },
    )


# ---------- Courses ----------


def create_draft_course(
    db: Session, principal: Principal, body: s.CourseDraftIn
) -> admin_s.CourseAdminOut:
    """A new course always starts as draft (review_status default)."""
    return catalog.create_course(
        db,
        principal,
        admin_s.CourseIn(
            title=body.title, role_profile=body.role_profile, description=body.description
        ),
    )


# ---------- Running AI jobs ----------


def _run[T: BaseModel](
    db: Session, job: AiJob, *, prompt_key: str, inputs: dict[str, Any], schema: type[T], stage: str
) -> T | None:
    job.status = AiJobStatus.running
    try:
        return gateway.complete_structured(
            db, prompt_key=prompt_key, inputs=inputs, schema=schema, stage=stage
        )
    except gateway.GatewayError as exc:
        job.status = AiJobStatus.failed
        job.error = str(exc)[:1000]
        return None


def _new_job(db: Session, principal: Principal, kind: AiJobKind, **fields: Any) -> AiJob:
    job = AiJob(kind=kind, requester_id=principal.user_id, status=AiJobStatus.queued, **fields)
    db.add(job)
    db.flush()
    return job


def draft_course(db: Session, principal: Principal, body: s.DraftRequest) -> s.JobOut:
    course = _get(db, Course, body.course_id, "Course")
    existing = list(
        db.scalars(
            select(Module.title).where(Module.course_id == course.id).order_by(Module.position)
        )
    )
    role = catalog.course_tree(db, course.id).role_profile
    inputs: dict[str, Any] = {
        "topic": gateway.delimit("topic", body.topic),
        "audience": body.audience,
        "level": body.level,
        "duration_weeks": body.duration_weeks,
        "role_profile": role,
        "trainer_notes": gateway.delimit("notes", body.notes),
        "existing_milestones": existing,
    }
    job = _new_job(
        db,
        principal,
        AiJobKind.draft_course,
        course_id=course.id,
        input=body.model_dump(mode="json"),
    )
    out = _run(
        db,
        job,
        prompt_key="author_draft_course",
        inputs=inputs,
        schema=s.CourseDraftOut,
        stage="author.draft",
    )
    if out is not None:
        have = {t.strip().lower() for t in existing}
        keep = [m for m in out.milestones if m.title.strip().lower() not in have]
        job.result = {
            "milestones": [m.model_dump() for m in keep],
            "dropped_duplicates": len(out.milestones) - len(keep),
        }
        job.status = AiJobStatus.ready
    return job_out(job)


def _latest_version(
    db: Session, filename: str, module_id: uuid.UUID | None, task_id: uuid.UUID | None
) -> int:
    query = select(func.max(CourseMaterial.version)).where(CourseMaterial.filename == filename)
    if module_id is not None:
        query = query.where(CourseMaterial.module_id == module_id)
    else:
        query = query.where(CourseMaterial.task_id == task_id)
    return db.scalar(query) or 0


def add_material(db: Session, principal: Principal, body: s.MaterialIn) -> s.MaterialOut:
    module_id, task_id, _ = _target(db, body.module_id, body.task_id)
    if len(body.text) > get_settings().max_text_chars:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The material is too long",
            f"The limit is {get_settings().max_text_chars} characters.",
        )
    name = body.filename.strip()
    if not name.lower().endswith((".md", ".txt")):
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Unsupported file type",
            "Upload a .md or .txt file, or paste text. Word and PDF are not supported yet.",
        )
    last = _latest_version(db, name, module_id, task_id)
    m = CourseMaterial(
        module_id=module_id,
        task_id=task_id,
        uploaded_by=principal.user_id,
        filename=name,
        storage_key="inline",
        content_type="text/markdown" if name.endswith(".md") else "text/plain",
        version=last + 1,
        extracted_text=body.text,
    )
    db.add(m)
    db.flush()
    _audit(
        db,
        principal,
        "material.add",
        "course_material",
        m.id,
        {"filename": name, "version": m.version},
    )
    return material_out(m)


def get_material(db: Session, principal: Principal, material_id: uuid.UUID) -> CourseMaterial:
    m = _get(db, CourseMaterial, material_id, "Material")
    if m.uploaded_by != principal.user_id and not is_admin(principal):
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Material not found")
    return m


def list_materials(
    db: Session, principal: Principal, module_id: uuid.UUID | None, task_id: uuid.UUID | None
) -> list[s.MaterialOut]:
    query = select(CourseMaterial).order_by(CourseMaterial.filename, CourseMaterial.version.desc())
    if module_id:
        query = query.where(CourseMaterial.module_id == module_id)
    if task_id:
        query = query.where(CourseMaterial.task_id == task_id)
    if not is_admin(principal):
        query = query.where(CourseMaterial.uploaded_by == principal.user_id)
    return [material_out(m) for m in db.scalars(query)]


def improve_material(
    db: Session, principal: Principal, material_id: uuid.UUID, body: s.ImproveRequest
) -> s.JobOut:
    material = get_material(db, principal, material_id)
    text = material.extracted_text or ""
    job = _new_job(
        db,
        principal,
        AiJobKind.improve_material,
        module_id=material.module_id,
        task_id=material.task_id,
        input={"material_id": str(material.id), "mode": body.mode},
    )
    inputs = {
        "mode": body.mode,
        "instruction": gateway.delimit("instruction", body.instruction),
        "material": gateway.delimit("material", text),
    }
    out = _run(
        db,
        job,
        prompt_key="author_improve_material",
        inputs=inputs,
        schema=s.ImproveOut,
        stage="author.improve",
    )
    if out is not None:
        # The model must quote the text exactly. Anything it cannot anchor is discarded, not guessed at.
        kept = [x for x in out.suggestions if x.original in text and x.proposed != x.original]
        job.result = {
            "material_id": str(material.id),
            "version": material.version,
            "suggestions": [x.model_dump() for x in kept],
            "dropped_unanchored": len(out.suggestions) - len(kept),
        }
        job.status = AiJobStatus.ready
    return job_out(job)


def attach_components(db: Session, principal: Principal, body: s.AttachRequest) -> s.JobOut:
    module_id, task_id, target = _target(db, body.module_id, body.task_id)
    job = _new_job(
        db,
        principal,
        AiJobKind.attach_components,
        module_id=module_id,
        task_id=task_id,
        input={"instruction": body.instruction},
    )
    inputs = {"instruction": gateway.delimit("instruction", body.instruction), "target": target}
    out = _run(
        db,
        job,
        prompt_key="author_attach_components",
        inputs=inputs,
        schema=s.AttachOut,
        stage="author.attach",
    )
    if out is not None:
        valid, dropped = [], 0
        for c in out.components:
            payload = s.validate_payload(c.type, c.payload)
            if payload is None:
                dropped += 1
            else:
                valid.append({"type": c.type, "title": c.title, "payload": payload})
        job.result = {"components": valid, "dropped_invalid": dropped}
        job.status = AiJobStatus.ready
    return job_out(job)


# ---------- Accepting or dismissing a proposal ----------


def dismiss(db: Session, principal: Principal, job_id: uuid.UUID) -> s.JobOut:
    job = own_job(db, principal, job_id)
    if job.status != AiJobStatus.ready:
        raise ProblemError(status.HTTP_409_CONFLICT, "Only a finished proposal can be dismissed")
    job.status = AiJobStatus.dismissed
    return job_out(job)


def accept(db: Session, principal: Principal, job_id: uuid.UUID, body: s.AcceptRequest) -> s.JobOut:
    job = own_job(db, principal, job_id)
    if job.status != AiJobStatus.ready or job.result is None:
        raise ProblemError(status.HTTP_409_CONFLICT, "There is no proposal to accept")
    key = {
        AiJobKind.draft_course: "milestones",
        AiJobKind.improve_material: "suggestions",
        AiJobKind.attach_components: "components",
    }[job.kind]
    items: list[dict[str, Any]] = job.result[key]
    chosen = sorted(set(body.items))
    if chosen[0] < 0 or chosen[-1] >= len(items):
        raise ProblemError(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose items from the proposal")
    picked = [items[i] for i in chosen]
    if job.kind == AiJobKind.draft_course:
        assert job.course_id is not None
        _accept_milestones(db, principal, job.course_id, picked)
    elif job.kind == AiJobKind.improve_material:
        _accept_suggestions(db, principal, job.result, picked)
    else:
        _accept_components(db, principal, job, picked)
    job.status = AiJobStatus.accepted
    _audit(
        db, principal, "ai_job.accept", "ai_job", job.id, {"kind": job.kind.value, "items": chosen}
    )
    return job_out(job)


def _accept_milestones(
    db: Session, principal: Principal, course_id: uuid.UUID, picked: list[dict[str, Any]]
) -> None:
    for m in picked:
        tree = catalog.create_module(
            db,
            principal,
            course_id,
            admin_s.ModuleIn(
                title=m["title"],
                description=m["description"],
                learning_objective=m["learning_objective"],
            ),
            draft=True,
        )
        module_id = tree.modules[-1].id
        for t in m["tasks"]:
            catalog.create_task(
                db,
                principal,
                module_id,
                admin_s.TaskIn(
                    title=t["title"],
                    task_type=t["task_type"],
                    description=t["description"],
                    learning_objective=t["learning_objective"],
                    submits=t["submits"],
                ),
            )


def _accept_suggestions(
    db: Session, principal: Principal, result: dict[str, Any], picked: list[dict[str, Any]]
) -> None:
    original = db.get(CourseMaterial, uuid.UUID(result["material_id"]))
    if original is None:
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Material not found")
    latest = _latest_version(db, original.filename, original.module_id, original.task_id)
    if latest > original.version:
        raise ProblemError(
            status.HTTP_409_CONFLICT,
            "The material has changed since these suggestions were made",
            "Run the check again on the latest version.",
        )
    text = original.extracted_text or ""
    applied = 0
    for sug in picked:
        if sug["original"] in text:  # skip if an earlier accepted edit already changed this part
            text = text.replace(sug["original"], sug["proposed"], 1)
            applied += 1
    if applied == 0:
        raise ProblemError(
            status.HTTP_409_CONFLICT, "None of the chosen edits still match the text"
        )
    last = (
        _latest_version(db, original.filename, original.module_id, original.task_id)
        or original.version
    )
    new = CourseMaterial(
        module_id=original.module_id,
        task_id=original.task_id,
        uploaded_by=original.uploaded_by,
        filename=original.filename,
        storage_key=original.storage_key,
        content_type=original.content_type,
        version=last + 1,
        extracted_text=text,
    )
    db.add(new)
    db.flush()
    _audit(
        db,
        principal,
        "material.ai_edit",
        "course_material",
        new.id,
        {"from_version": original.version, "version": new.version, "edits": applied},
    )


def _accept_components(
    db: Session, principal: Principal, job: AiJob, picked: list[dict[str, Any]]
) -> None:
    for c in picked:
        payload = s.validate_payload(c["type"], c["payload"])
        if payload is None:
            continue
        row = CourseComponent(
            module_id=job.module_id,
            task_id=job.task_id,
            type=ComponentType(c["type"]),
            title=c["title"],
            payload=payload,
            review_status="draft",
            ai_generated=True,
            ai_job_id=job.id,
            created_by=principal.user_id,
        )
        db.add(row)
        db.flush()
        _audit(
            db, principal, "component.create", "course_component", row.id, {"ai_generated": True}
        )


# ---------- Material becomes study material ----------


def publish_material(
    db: Session, principal: Principal, material_id: uuid.UUID, body: s.PublishMaterialIn
) -> s.ComponentOut:
    """Turn a material version into a draft reading note. It still needs admin approval."""
    material = get_material(db, principal, material_id)
    if material.module_id is None:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Only milestone material can be published"
        )
    text = (material.extracted_text or "").strip()
    if not text:
        raise ProblemError(status.HTTP_422_UNPROCESSABLE_ENTITY, "The material is empty")
    title = (body.title or material.filename.rsplit(".", 1)[0]).strip()
    row = CourseComponent(
        module_id=material.module_id,
        type=ComponentType.reading_note,
        title=title[:200],
        payload={
            "body": text,
            "source_material_id": str(material.id),
            "source_version": material.version,
        },
        review_status="draft",
        ai_generated=False,
        created_by=principal.user_id,
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        principal,
        "component.create",
        "course_component",
        row.id,
        {"from_material": str(material.id), "version": material.version},
    )
    return component_out(row)


# ---------- What a learner studies ----------


def study_material(db: Session, principal: Principal, module_id: uuid.UUID) -> s.StudyOut:
    """Approved study items for one milestone, module-level first, then per task.

    Interns: only for a milestone in a course they are enrolled in that is open or complete.
    Staff (trainer, HR, admin): any approved milestone. Drafts are never returned here.
    """
    module = db.get(Module, module_id)
    if module is None or module.review_status != "approved":
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Milestone not found")
    is_staff = has_any(
        principal.roles,
        Permission.CATALOG_DRAFT,
        Permission.COHORT_OVERVIEW,
        Permission.CATALOG_MANAGE,
    )
    if not is_staff:
        progress = db.scalar(
            select(MilestoneProgress.status)
            .join(Enrollment, Enrollment.id == MilestoneProgress.enrollment_id)
            .where(
                Enrollment.user_id == principal.user_id, MilestoneProgress.module_id == module.id
            )
        )
        if progress is None:
            raise ProblemError(
                status.HTTP_404_NOT_FOUND, "Milestone not found"
            )  # no existence leak
        if progress == "locked":
            raise ProblemError(status.HTTP_403_FORBIDDEN, "This milestone is not open yet")
    task_ids = list(db.scalars(select(TaskTemplate.id).where(TaskTemplate.module_id == module.id)))
    rows = db.scalars(
        select(CourseComponent)
        .where(
            CourseComponent.review_status == "approved",
            (CourseComponent.module_id == module.id) | CourseComponent.task_id.in_(task_ids),
        )
        .order_by(CourseComponent.task_id.is_not(None), CourseComponent.created_at)
    )
    items = [
        s.StudyItem(
            id=c.id,
            type=c.type.value,
            title=c.title,
            payload={
                k: v
                for k, v in c.payload.items()
                if k not in {"source_material_id", "source_version"}
            },
            ai_generated=c.ai_generated,
            task_id=c.task_id,
        )
        for c in rows
    ]
    return s.StudyOut(module_id=module.id, items=items)


# ---------- Admin approvals queue ----------


def pending_approvals(db: Session) -> s.PendingOut:
    """Draft milestones and components waiting for an admin (router enforces admin only)."""
    modules = []
    for m, c in db.execute(
        select(Module, Course)
        .join(Course, Course.id == Module.course_id)
        .where(Module.review_status == "draft")
        .order_by(Course.title, Module.position)
    ):
        modules.append(
            s.PendingModule(
                course_id=c.id,
                course_title=c.title,
                module_id=m.id,
                title=m.title,
                created_by=m.created_by,
            )
        )
    components = []
    for comp in db.scalars(
        select(CourseComponent)
        .where(CourseComponent.review_status == "in_review")
        .order_by(CourseComponent.updated_at)
    ):
        context = None
        if comp.module_id:
            mod = db.get(Module, comp.module_id)
            context = mod.title if mod else None
        elif comp.task_id:
            task = db.get(TaskTemplate, comp.task_id)
            context = task.title if task else None
        components.append(s.PendingComponent(component=component_out(comp), context=context))
    return s.PendingOut(modules=modules, components=components)


# ---------- Components (manual) ----------


def list_components(
    db: Session, principal: Principal, module_id: uuid.UUID | None, task_id: uuid.UUID | None
) -> list[s.ComponentOut]:
    query = select(CourseComponent).order_by(CourseComponent.created_at)
    if module_id:
        query = query.where(CourseComponent.module_id == module_id)
    if task_id:
        query = query.where(CourseComponent.task_id == task_id)
    if not is_admin(principal):
        query = query.where(CourseComponent.created_by == principal.user_id)
    return [component_out(c) for c in db.scalars(query)]


def create_component(db: Session, principal: Principal, body: s.ComponentIn) -> s.ComponentOut:
    module_id, task_id, _ = _target(db, body.module_id, body.task_id)
    payload = s.validate_payload(body.type, body.payload)
    if payload is None:
        raise ProblemError(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "The content does not fit this component type"
        )
    row = CourseComponent(
        module_id=module_id,
        task_id=task_id,
        type=ComponentType(body.type),
        title=body.title.strip(),
        payload=payload,
        review_status="draft",
        ai_generated=False,
        created_by=principal.user_id,
    )
    db.add(row)
    db.flush()
    _audit(db, principal, "component.create", "course_component", row.id, {"ai_generated": False})
    return component_out(row)


def _editable(db: Session, principal: Principal, component_id: uuid.UUID) -> CourseComponent:
    row = _get(db, CourseComponent, component_id, "Component")
    if row.created_by != principal.user_id and not is_admin(principal):
        raise ProblemError(status.HTTP_404_NOT_FOUND, "Component not found")
    return row


def update_component(
    db: Session, principal: Principal, component_id: uuid.UUID, body: s.ComponentPatch
) -> s.ComponentOut:
    row = _editable(db, principal, component_id)
    if row.review_status == "approved" and not is_admin(principal):
        raise ProblemError(
            status.HTTP_409_CONFLICT, "Approved components can only be changed by an admin"
        )
    if body.title is not None:
        row.title = body.title.strip()
    if body.payload is not None:
        payload = s.validate_payload(row.type.value, body.payload)
        if payload is None:
            raise ProblemError(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "The content does not fit this component type"
            )
        row.payload = payload
    # Any edit needs a fresh review.
    row.review_status, row.approved_by, row.approved_at = "draft", None, None
    db.flush()
    return component_out(row)


def delete_component(db: Session, principal: Principal, component_id: uuid.UUID) -> None:
    row = _editable(db, principal, component_id)
    if row.review_status == "approved" and not is_admin(principal):
        raise ProblemError(
            status.HTTP_409_CONFLICT, "Approved components can only be removed by an admin"
        )
    db.delete(row)
    db.flush()


def submit_component(db: Session, principal: Principal, component_id: uuid.UUID) -> s.ComponentOut:
    row = _editable(db, principal, component_id)
    if row.review_status != "draft":
        raise ProblemError(status.HTTP_409_CONFLICT, "Only a draft can be sent for review")
    row.review_status = "in_review"
    db.flush()
    return component_out(row)


def approve_component(db: Session, principal: Principal, component_id: uuid.UUID) -> s.ComponentOut:
    """Admin only (enforced by the router). Approval is always a person's decision."""
    row = _get(db, CourseComponent, component_id, "Component")
    if row.type == ComponentType.resource and not row.payload.get("link_verified"):
        raise ProblemError(
            status.HTTP_409_CONFLICT,
            "Confirm the link first",
            "Open the link, check it, and mark it verified before approving.",
        )
    row.review_status, row.approved_by, row.approved_at = (
        "approved",
        principal.user_id,
        datetime.now(UTC),
    )
    db.flush()
    _audit(db, principal, "component.approve", "course_component", row.id)
    return component_out(row)


def verify_link(db: Session, principal: Principal, component_id: uuid.UUID) -> s.ComponentOut:
    """The person who checked the link confirms it. The AI never sets this flag."""
    row = _editable(db, principal, component_id)
    if row.type != ComponentType.resource:
        raise ProblemError(status.HTTP_409_CONFLICT, "Only links can be verified")
    row.payload = {**row.payload, "link_verified": True}
    db.flush()
    return component_out(row)


# ---------- Trainer edits to their own draft milestones ----------


def _own_draft_module(db: Session, principal: Principal, module: Module) -> None:
    if is_admin(principal):
        return
    if module.review_status != "draft" or module.created_by != principal.user_id:
        raise ProblemError(
            status.HTTP_403_FORBIDDEN, "You can only edit draft milestones you created"
        )


def update_module(
    db: Session, principal: Principal, module_id: uuid.UUID, body: admin_s.ModulePatch
) -> admin_s.CourseAdminOut:
    module = _get(db, Module, module_id, "Milestone")
    _own_draft_module(db, principal, module)
    return catalog.update_module(db, principal, module_id, body)


def update_task(
    db: Session, principal: Principal, task_id: uuid.UUID, body: admin_s.TaskPatch
) -> admin_s.CourseAdminOut:
    task = _get(db, TaskTemplate, task_id, "Task")
    _own_draft_module(db, principal, _get(db, Module, task.module_id, "Milestone"))
    return catalog.update_task(db, principal, task_id, body)
