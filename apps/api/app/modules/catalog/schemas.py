"""Catalog API response models."""

import uuid
from typing import Any

from pydantic import BaseModel


class CourseOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    description: str
    role_profile: str
    milestone_count: int
    review_status: str


class TaskSummaryOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    task_type: str
    depth: str


class ModuleOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    position: int
    description: str
    tasks: list[TaskSummaryOut]


class CriterionOut(BaseModel):
    """A rubric criterion as shown to interns before they start (FR-INT-03)."""

    id: str
    title: str
    weight: int
    mandatory: bool
    mandatory_min_level: int | None
    levels: dict[str, str]


class DeliverableOut(BaseModel):
    id: str
    title: str
    description: str = ""
    kinds: list[str]  # accepted alternatives, e.g. ["file", "link"]
    required: bool
    accept: list[str] = []
    min_words: int | None = None
    max_words: int | None = None
    min_count: int | None = None
    max_count: int | None = None
    min_items: int | None = None
    sections: list[str] = []


class RubricOut(BaseModel):
    """Published rubric in plain language. Checker bindings are not exposed."""

    rubric_id: str
    version: int
    pass_threshold: float
    criteria: list[CriterionOut]


class TaskTemplateOut(BaseModel):
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
    starter_files: list[str]
    deliverables: list[DeliverableOut]  # the task's manifest (Architecture 6.1)
    rubric: RubricOut | None


def rubric_out(content: dict[str, Any]) -> RubricOut:
    return RubricOut(
        rubric_id=content["rubric_id"],
        version=content["version"],
        pass_threshold=content["pass_threshold"],
        criteria=[
            CriterionOut(
                id=c["id"],
                # Tech lead decision 4: title is optional; the API always returns a non-empty
                # title, falling back to the stable id. The frontend never derives its own.
                title=c.get("title") or c["id"],
                weight=c["weight"],
                mandatory=c.get("mandatory_min_level") is not None,
                mandatory_min_level=c.get("mandatory_min_level"),
                levels=c["levels"],
            )
            for c in content["criteria"]
        ],
    )


def kinds_of(d: dict[str, Any]) -> list[str]:
    return d["kind"] if isinstance(d["kind"], list) else [d["kind"]]


def deliverable_out(d: dict[str, Any]) -> DeliverableOut:
    return DeliverableOut(
        id=d["id"],
        title=d.get("title") or d["id"],
        description=d.get("description", ""),
        kinds=kinds_of(d),
        required=d["required"],
        accept=d.get("accept", []),
        min_words=d.get("min_words"),
        max_words=d.get("max_words"),
        min_count=d.get("min_count"),
        max_count=d.get("max_count"),
        min_items=d.get("min_items"),
        sections=d.get("sections", []),
    )
