"""Admin API models."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

from app.modules.catalog.schemas import CriterionOut, DeliverableOut

RoleKey = Literal["developer", "ba", "qa", "uiux"]


class RoleProfileOut(BaseModel):
    key: str
    name: str
    checkers: list[str]
    always_review: bool


# ---------- Courses ----------


class CourseIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    role_profile: RoleKey
    description: str = Field(default="", max_length=5000)
    final_deliverable: str = Field(default="", max_length=2000)


class CoursePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    final_deliverable: str | None = Field(default=None, max_length=2000)
    review_status: Literal["draft", "approved"] | None = None


class ModuleIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    learning_objective: str = Field(default="", max_length=2000)


class ModulePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    learning_objective: str | None = Field(default=None, max_length=2000)


class ModuleOrderIn(BaseModel):
    module_ids: list[uuid.UUID] = Field(min_length=1)


class DeliverableIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$", max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    kind: list[Literal["file", "link", "text"]] = Field(min_length=1)
    required: bool = True
    accept: list[str] = Field(default_factory=list)
    min_words: int | None = Field(default=None, ge=1)
    max_words: int | None = Field(default=None, ge=1)
    min_count: int | None = Field(default=None, ge=1)
    max_count: int | None = Field(default=None, ge=1)
    min_items: int | None = Field(default=None, ge=1)
    sections: list[str] = Field(default_factory=list)


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    task_type: Literal["practical", "integration", "assessment"] = "practical"
    depth: Literal["demo", "content"] = "content"
    description: str = Field(min_length=1, max_length=10000)
    learning_objective: str = Field(default="", max_length=2000)
    submits: str = Field(default="", max_length=2000)
    evaluated_on: str = Field(default="", max_length=2000)
    requires_review: bool = False
    deliverables: list[DeliverableIn] | None = None  # omitted: the generic one-item manifest


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    task_type: Literal["practical", "integration", "assessment"] | None = None
    depth: Literal["demo", "content"] | None = None
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    learning_objective: str | None = Field(default=None, max_length=2000)
    submits: str | None = Field(default=None, max_length=2000)
    evaluated_on: str | None = Field(default=None, max_length=2000)
    requires_review: bool | None = None
    deliverables: list[DeliverableIn] | None = None


class CriterionIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$", max_length=100)
    title: str = Field(min_length=1, max_length=200)
    weight: int = Field(ge=1, le=100)
    mandatory_min_level: int | None = Field(default=None, ge=1, le=4)
    levels: dict[Literal["0", "1", "2", "3", "4"], str]
    bound_checks: list[str] = Field(default_factory=list)
    correction_template: str = Field(default="", max_length=200)


class RubricDraftIn(BaseModel):
    """Drafts may be incomplete. Publishing validates everything."""

    pass_threshold: float = Field(default=70, ge=0, le=100)
    criteria: list[CriterionIn] = Field(default_factory=list)
    checkers: list[str] = Field(default_factory=list)


class RubricOutAdmin(BaseModel):
    id: uuid.UUID
    version: int
    published: bool
    pass_threshold: float
    criteria: list[CriterionOut]
    checkers: list[str]
    content: dict[str, Any]


class TaskAdminOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    task_type: str
    depth: str
    description: str
    learning_objective: str
    submits: str
    evaluated_on: str
    requires_review: bool
    deliverables: list[DeliverableOut]
    published_rubric: RubricOutAdmin | None
    draft_rubric: RubricOutAdmin | None


class ModuleAdminOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    position: int
    description: str
    learning_objective: str
    review_status: str = "approved"
    created_by: uuid.UUID | None = None
    tasks: list[TaskAdminOut]


class CourseAdminOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    role_profile: str
    description: str
    final_deliverable: str
    review_status: str
    enrollment_count: int
    modules: list[ModuleAdminOut]


class CourseSummaryOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    role_profile: str
    review_status: str
    milestone_count: int
    task_count: int
    enrollment_count: int
    updated_at: datetime


# ---------- Cohorts and users ----------


class CohortIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    starts_on: date | None = None
    trainer_id: uuid.UUID | None = None


class CohortPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    starts_on: date | None = None
    trainer_id: uuid.UUID | None = None


class EnrollmentIn(BaseModel):
    user_id: uuid.UUID
    course_id: uuid.UUID


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    intern_name: str
    intern_email: str
    course_id: uuid.UUID
    course_title: str
    milestones_complete: int
    milestones_total: int


class CohortOut(BaseModel):
    id: uuid.UUID
    name: str
    starts_on: date | None
    trainer_id: uuid.UUID | None
    trainer_name: str | None
    enrollment_count: int


class CohortDetailOut(CohortOut):
    enrollments: list[EnrollmentOut]


class UserIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role: Literal["intern", "trainer", "hr", "admin"]
    password: str = Field(min_length=12, max_length=1024)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    roles: list[str]
    created_at: datetime
