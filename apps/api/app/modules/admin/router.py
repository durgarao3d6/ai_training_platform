"""Admin endpoints: course authoring (admin) and cohorts, enrollments, users (HR and admin)."""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.admin import catalog_service as catalog
from app.modules.admin import cohort_service as cohorts
from app.modules.admin import schemas as s
from app.modules.identity.deps import Principal, get_scoped_db, require_permission
from app.modules.identity.permissions import Permission

router = APIRouter(prefix="/admin", tags=["admin"])

_author = require_permission(Permission.CATALOG_MANAGE)
_manage = require_permission(Permission.COHORT_MANAGE)
_users = require_permission(Permission.USERS_MANAGE_INTERNS, Permission.USERS_MANAGE_ALL)


# ---------- Catalog authoring ----------


@router.get(
    "/role-profiles", response_model=list[s.RoleProfileOut], dependencies=[Depends(_author)]
)
def role_profiles(db: Session = Depends(get_scoped_db)) -> list[s.RoleProfileOut]:
    return catalog.role_profiles(db)


@router.get("/courses", response_model=list[s.CourseSummaryOut])
def list_courses(
    _: Principal = Depends(require_permission(Permission.CATALOG_MANAGE, Permission.COHORT_MANAGE)),
    db: Session = Depends(get_scoped_db),
) -> list[s.CourseSummaryOut]:
    return catalog.list_courses(db)


@router.post("/courses", response_model=s.CourseAdminOut, status_code=status.HTTP_201_CREATED)
def create_course(
    body: s.CourseIn, p: Principal = Depends(_author), db: Session = Depends(get_scoped_db)
) -> s.CourseAdminOut:
    return catalog.create_course(db, p, body)


@router.get(
    "/courses/{course_id}", response_model=s.CourseAdminOut, dependencies=[Depends(_author)]
)
def get_course(course_id: uuid.UUID, db: Session = Depends(get_scoped_db)) -> s.CourseAdminOut:
    return catalog.course_tree(db, course_id)


@router.patch("/courses/{course_id}", response_model=s.CourseAdminOut)
def update_course(
    course_id: uuid.UUID,
    body: s.CoursePatch,
    p: Principal = Depends(_author),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.update_course(db, p, course_id, body)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: uuid.UUID, p: Principal = Depends(_author), db: Session = Depends(get_scoped_db)
) -> Response:
    catalog.delete_course(db, p, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/courses/{course_id}/modules",
    response_model=s.CourseAdminOut,
    status_code=status.HTTP_201_CREATED,
)
def create_module(
    course_id: uuid.UUID,
    body: s.ModuleIn,
    p: Principal = Depends(_author),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.create_module(db, p, course_id, body)


@router.put("/courses/{course_id}/module-order", response_model=s.CourseAdminOut)
def reorder_modules(
    course_id: uuid.UUID,
    body: s.ModuleOrderIn,
    p: Principal = Depends(_author),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.reorder_modules(db, p, course_id, body)


@router.patch("/modules/{module_id}", response_model=s.CourseAdminOut)
def update_module(
    module_id: uuid.UUID,
    body: s.ModulePatch,
    p: Principal = Depends(_author),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.update_module(db, p, module_id, body)


@router.delete("/modules/{module_id}", response_model=s.CourseAdminOut)
def delete_module(
    module_id: uuid.UUID, p: Principal = Depends(_author), db: Session = Depends(get_scoped_db)
) -> s.CourseAdminOut:
    return catalog.delete_module(db, p, module_id)


@router.post(
    "/modules/{module_id}/tasks",
    response_model=s.CourseAdminOut,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    module_id: uuid.UUID,
    body: s.TaskIn,
    p: Principal = Depends(_author),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.create_task(db, p, module_id, body)


@router.patch("/tasks/{task_id}", response_model=s.CourseAdminOut)
def update_task(
    task_id: uuid.UUID,
    body: s.TaskPatch,
    p: Principal = Depends(_author),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.update_task(db, p, task_id, body)


@router.delete("/tasks/{task_id}", response_model=s.CourseAdminOut)
def delete_task(
    task_id: uuid.UUID, p: Principal = Depends(_author), db: Session = Depends(get_scoped_db)
) -> s.CourseAdminOut:
    return catalog.delete_task(db, p, task_id)


@router.put("/tasks/{task_id}/rubric-draft", response_model=s.CourseAdminOut)
def save_rubric_draft(
    task_id: uuid.UUID,
    body: s.RubricDraftIn,
    p: Principal = Depends(require_permission(Permission.RUBRIC_DRAFT)),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.save_rubric_draft(db, p, task_id, body)


@router.post("/tasks/{task_id}/rubric-draft/publish", response_model=s.CourseAdminOut)
def publish_rubric(
    task_id: uuid.UUID,
    p: Principal = Depends(require_permission(Permission.RUBRIC_PUBLISH)),
    db: Session = Depends(get_scoped_db),
) -> s.CourseAdminOut:
    return catalog.publish_rubric(db, p, task_id)


# ---------- Cohorts and enrollments ----------


@router.get("/cohorts", response_model=list[s.CohortOut], dependencies=[Depends(_manage)])
def list_cohorts(db: Session = Depends(get_scoped_db)) -> list[s.CohortOut]:
    return cohorts.list_cohorts(db)


@router.post("/cohorts", response_model=s.CohortDetailOut, status_code=status.HTTP_201_CREATED)
def create_cohort(
    body: s.CohortIn, p: Principal = Depends(_manage), db: Session = Depends(get_scoped_db)
) -> s.CohortDetailOut:
    return cohorts.create_cohort(db, p, body)


@router.get(
    "/cohorts/{cohort_id}", response_model=s.CohortDetailOut, dependencies=[Depends(_manage)]
)
def get_cohort(cohort_id: uuid.UUID, db: Session = Depends(get_scoped_db)) -> s.CohortDetailOut:
    return cohorts.cohort_detail(db, cohort_id)


@router.patch("/cohorts/{cohort_id}", response_model=s.CohortDetailOut)
def update_cohort(
    cohort_id: uuid.UUID,
    body: s.CohortPatch,
    p: Principal = Depends(_manage),
    db: Session = Depends(get_scoped_db),
) -> s.CohortDetailOut:
    return cohorts.update_cohort(db, p, cohort_id, body)


@router.post(
    "/cohorts/{cohort_id}/enrollments",
    response_model=s.CohortDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def enroll(
    cohort_id: uuid.UUID,
    body: s.EnrollmentIn,
    p: Principal = Depends(_manage),
    db: Session = Depends(get_scoped_db),
) -> s.CohortDetailOut:
    return cohorts.enroll(db, p, cohort_id, body)


# ---------- Users ----------


@router.get("/users", response_model=list[s.UserOut], dependencies=[Depends(_users)])
def list_users(
    role: str | None = Query(default=None, pattern="^(intern|trainer|hr|admin)$"),
    db: Session = Depends(get_scoped_db),
) -> list[s.UserOut]:
    return cohorts.list_users(db, role)


@router.post("/users", response_model=s.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: s.UserIn, p: Principal = Depends(_users), db: Session = Depends(get_scoped_db)
) -> s.UserOut:
    return cohorts.create_user(db, p, body)
