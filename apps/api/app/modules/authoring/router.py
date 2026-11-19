"""Authoring endpoints. Trainers and admins draft; only admins approve (open questions 7.1)."""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.admin import catalog_service as catalog
from app.modules.admin import schemas as admin_s
from app.modules.authoring import schemas as s
from app.modules.authoring import service
from app.modules.identity.deps import Principal, get_scoped_db, require_permission
from app.modules.identity.permissions import Permission

router = APIRouter(prefix="/authoring", tags=["authoring"])
# Learner-facing reads live outside /authoring so interns are not routed through authoring paths.
study_router = APIRouter(tags=["study"])

_draft = require_permission(Permission.CATALOG_DRAFT)
_approve = require_permission(Permission.CATALOG_MANAGE)
# AI endpoints are behind the AI_AUTHORING_ENABLED flag (404 when off).
_ai = [Depends(service.require_enabled)]


@router.get("/config", response_model=s.ConfigOut, dependencies=[Depends(_draft)])
def config() -> s.ConfigOut:
    settings = get_settings()
    return s.ConfigOut(
        ai_enabled=settings.ai_authoring_enabled,
        ai_mode="live" if settings.llm_mode == "live" else "fixture",
    )


@router.get("/pending", response_model=s.PendingOut, dependencies=[Depends(_approve)])
def pending(db: Session = Depends(get_scoped_db)) -> s.PendingOut:
    return service.pending_approvals(db)


# ---------- Reading courses (trainers cannot use the admin routes) ----------


@router.get("/courses", response_model=list[admin_s.CourseSummaryOut])
def list_courses(
    _: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> list[admin_s.CourseSummaryOut]:
    return catalog.list_courses(db)


@router.get(
    "/courses/{course_id}", response_model=admin_s.CourseAdminOut, dependencies=[Depends(_draft)]
)
def get_course(
    course_id: uuid.UUID, db: Session = Depends(get_scoped_db)
) -> admin_s.CourseAdminOut:
    return catalog.course_tree(db, course_id)


@router.post("/courses", response_model=admin_s.CourseAdminOut, status_code=status.HTTP_201_CREATED)
def create_course(
    body: s.CourseDraftIn, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> admin_s.CourseAdminOut:
    return service.create_draft_course(db, p, body)


@router.patch("/modules/{module_id}", response_model=admin_s.CourseAdminOut)
def update_module(
    module_id: uuid.UUID,
    body: admin_s.ModulePatch,
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> admin_s.CourseAdminOut:
    return service.update_module(db, p, module_id, body)


@router.patch("/tasks/{task_id}", response_model=admin_s.CourseAdminOut)
def update_task(
    task_id: uuid.UUID,
    body: admin_s.TaskPatch,
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> admin_s.CourseAdminOut:
    return service.update_task(db, p, task_id, body)


@router.post("/modules/{module_id}/approve", response_model=admin_s.CourseAdminOut)
def approve_module(
    module_id: uuid.UUID, p: Principal = Depends(_approve), db: Session = Depends(get_scoped_db)
) -> admin_s.CourseAdminOut:
    return catalog.approve_module(db, p, module_id)


# ---------- AI jobs ----------


@router.post(
    "/drafts", response_model=s.JobOut, status_code=status.HTTP_201_CREATED, dependencies=_ai
)
def draft_course(
    body: s.DraftRequest, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.JobOut:
    return service.draft_course(db, p, body)


@router.post(
    "/attach", response_model=s.JobOut, status_code=status.HTTP_201_CREATED, dependencies=_ai
)
def attach(
    body: s.AttachRequest, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.JobOut:
    return service.attach_components(db, p, body)


@router.post(
    "/materials/{material_id}/improve",
    response_model=s.JobOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=_ai,
)
def improve(
    material_id: uuid.UUID,
    body: s.ImproveRequest,
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> s.JobOut:
    return service.improve_material(db, p, material_id, body)


@router.get("/jobs/{job_id}", response_model=s.JobOut)
def get_job(
    job_id: uuid.UUID, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.JobOut:
    return service.job_out(service.own_job(db, p, job_id))


@router.post("/jobs/{job_id}/accept", response_model=s.JobOut)
def accept(
    job_id: uuid.UUID,
    body: s.AcceptRequest,
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> s.JobOut:
    return service.accept(db, p, job_id, body)


@router.post("/jobs/{job_id}/dismiss", response_model=s.JobOut)
def dismiss(
    job_id: uuid.UUID, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.JobOut:
    return service.dismiss(db, p, job_id)


# ---------- Materials ----------


@router.post("/materials", response_model=s.MaterialOut, status_code=status.HTTP_201_CREATED)
def add_material(
    body: s.MaterialIn, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.MaterialOut:
    return service.add_material(db, p, body)


@router.get("/materials", response_model=list[s.MaterialOut])
def list_materials(
    module_id: uuid.UUID | None = Query(default=None),
    task_id: uuid.UUID | None = Query(default=None),
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> list[s.MaterialOut]:
    return service.list_materials(db, p, module_id, task_id)


@router.post(
    "/materials/{material_id}/publish",
    response_model=s.ComponentOut,
    status_code=status.HTTP_201_CREATED,
)
def publish_material(
    material_id: uuid.UUID,
    body: s.PublishMaterialIn,
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> s.ComponentOut:
    return service.publish_material(db, p, material_id, body)


# ---------- Study material for learners ----------

_study = require_permission(
    Permission.SUBMISSION_READ_OWN,
    Permission.CATALOG_DRAFT,
    Permission.COHORT_OVERVIEW,
    Permission.CATALOG_MANAGE,
)


@study_router.get("/modules/{module_id}/study", response_model=s.StudyOut)
def study(
    module_id: uuid.UUID, p: Principal = Depends(_study), db: Session = Depends(get_scoped_db)
) -> s.StudyOut:
    return service.study_material(db, p, module_id)


# ---------- Components ----------


@router.get("/components", response_model=list[s.ComponentOut])
def list_components(
    module_id: uuid.UUID | None = Query(default=None),
    task_id: uuid.UUID | None = Query(default=None),
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> list[s.ComponentOut]:
    return service.list_components(db, p, module_id, task_id)


@router.post("/components", response_model=s.ComponentOut, status_code=status.HTTP_201_CREATED)
def create_component(
    body: s.ComponentIn, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.ComponentOut:
    return service.create_component(db, p, body)


@router.patch("/components/{component_id}", response_model=s.ComponentOut)
def update_component(
    component_id: uuid.UUID,
    body: s.ComponentPatch,
    p: Principal = Depends(_draft),
    db: Session = Depends(get_scoped_db),
) -> s.ComponentOut:
    return service.update_component(db, p, component_id, body)


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_component(
    component_id: uuid.UUID, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> Response:
    service.delete_component(db, p, component_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/components/{component_id}/submit", response_model=s.ComponentOut)
def submit_component(
    component_id: uuid.UUID, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.ComponentOut:
    return service.submit_component(db, p, component_id)


@router.post("/components/{component_id}/verify-link", response_model=s.ComponentOut)
def verify_link(
    component_id: uuid.UUID, p: Principal = Depends(_draft), db: Session = Depends(get_scoped_db)
) -> s.ComponentOut:
    return service.verify_link(db, p, component_id)


@router.post("/components/{component_id}/approve", response_model=s.ComponentOut)
def approve_component(
    component_id: uuid.UUID, p: Principal = Depends(_approve), db: Session = Depends(get_scoped_db)
) -> s.ComponentOut:
    return service.approve_component(db, p, component_id)
