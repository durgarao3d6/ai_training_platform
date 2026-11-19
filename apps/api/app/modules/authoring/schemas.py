"""Authoring API and AI output models.

The *Out models named *Draft/ImproveOut/AttachOut are the strict schemas the LLM must satisfy.
Everything the model returns is a proposal until a person accepts it.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------- AI output: course draft ----------


class TaskDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    task_type: Literal["practical", "integration", "assessment"] = "practical"
    description: str = Field(min_length=1, max_length=2000)
    learning_objective: str = Field(default="", max_length=500)
    submits: str = Field(default="", max_length=500)


class MilestoneDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    learning_objective: str = Field(min_length=1, max_length=500)
    tasks: list[TaskDraft] = Field(min_length=1, max_length=3)


class CourseDraftOut(BaseModel):
    milestones: list[MilestoneDraft] = Field(min_length=1, max_length=15)


# ---------- AI output: material suggestions ----------

Category = Literal["correction", "clarity", "structure", "example", "objective_alignment"]


class Suggestion(BaseModel):
    original: str = Field(min_length=1, max_length=1000)
    proposed: str = Field(max_length=2000)
    reason: str = Field(default="", max_length=300)
    category: Category = "clarity"


class ImproveOut(BaseModel):
    suggestions: list[Suggestion] = Field(max_length=50)


# ---------- Components (AI output and manual) ----------

ComponentKind = Literal["resource", "reading_note", "quiz", "starter_file"]


class ResourcePayload(BaseModel):
    url: str = Field(max_length=2000)
    note: str = Field(default="", max_length=500)

    @field_validator("url")
    @classmethod
    def https_only(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Links must start with https://")
        return v


class ReadingPayload(BaseModel):
    # Long enough for a trainer's full material (same limit as uploads). The AI prompt asks for less.
    body: str = Field(min_length=1, max_length=50_000)


class QuizQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=5)
    correct_index: int = Field(ge=0, le=4)
    explanation: str = Field(default="", max_length=500)


class QuizPayload(BaseModel):
    questions: list[QuizQuestion] = Field(min_length=1, max_length=10)

    @field_validator("questions")
    @classmethod
    def index_in_range(cls, v: list[QuizQuestion]) -> list[QuizQuestion]:
        for q in v:
            if q.correct_index >= len(q.options):
                raise ValueError("correct_index must point at one of the options")
        return v


class StarterPayload(BaseModel):
    filename: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._-]+$")
    description: str = Field(default="", max_length=500)


PAYLOADS: dict[str, type[BaseModel]] = {
    "resource": ResourcePayload,
    "reading_note": ReadingPayload,
    "quiz": QuizPayload,
    "starter_file": StarterPayload,
}


def validate_payload(kind: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return the cleaned payload, or None when it does not fit the component type."""
    model = PAYLOADS.get(kind)
    if model is None:
        return None
    try:
        data = model.model_validate(payload).model_dump()
    except ValidationError:
        return None
    if kind == "resource":
        data["link_verified"] = False  # a person must confirm the link works and is appropriate
    return data


class ComponentDraft(BaseModel):
    type: ComponentKind
    title: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any]


class AttachOut(BaseModel):
    components: list[ComponentDraft] = Field(max_length=10)


# ---------- Requests ----------


class CourseDraftIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    role_profile: Literal["developer", "ba", "qa", "uiux"]
    description: str = Field(default="", max_length=5000)


class DraftRequest(BaseModel):
    course_id: uuid.UUID
    topic: str = Field(min_length=1, max_length=300)
    audience: str = Field(default="", max_length=200)
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    duration_weeks: int = Field(default=4, ge=1, le=52)
    notes: str = Field(default="", max_length=2000)


class MaterialIn(BaseModel):
    module_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)


class ImproveRequest(BaseModel):
    mode: Literal["correct", "enhance"]
    instruction: str = Field(default="", max_length=1000)


class AttachRequest(BaseModel):
    module_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    instruction: str = Field(min_length=1, max_length=1000)


class AcceptRequest(BaseModel):
    items: list[int] = Field(min_length=1)


class ComponentIn(BaseModel):
    module_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    type: ComponentKind
    title: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any]


class ComponentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    payload: dict[str, Any] | None = None


# ---------- Responses ----------


class MaterialOut(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID | None
    task_id: uuid.UUID | None
    filename: str
    version: int
    text: str
    created_at: datetime


class JobOut(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    course_id: uuid.UUID | None
    module_id: uuid.UUID | None
    task_id: uuid.UUID | None
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime


class ConfigOut(BaseModel):
    ai_enabled: bool
    ai_mode: Literal["fixture", "live"]


class PendingModule(BaseModel):
    course_id: uuid.UUID
    course_title: str
    module_id: uuid.UUID
    title: str
    created_by: uuid.UUID | None


class ComponentOut(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID | None
    task_id: uuid.UUID | None
    type: str
    title: str
    payload: dict[str, Any]
    review_status: str
    ai_generated: bool
    created_by: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None


class PendingComponent(BaseModel):
    component: ComponentOut
    context: str | None


class PendingOut(BaseModel):
    modules: list[PendingModule]
    components: list[PendingComponent]


class PublishMaterialIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class StudyItem(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    payload: dict[str, Any]
    ai_generated: bool
    task_id: uuid.UUID | None


class StudyOut(BaseModel):
    module_id: uuid.UUID
    items: list[StudyItem]
