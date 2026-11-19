"""Trainer-led review contracts."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReviewInput(BaseModel):
    decision: Literal["approve", "request_revision"]
    rubric_version_id: uuid.UUID
    reason: str = Field(max_length=5000)


class ReviewResult(BaseModel):
    decision: Literal["approve", "request_revision"]
    reason: str
    decided_at: datetime
    rubric_version_id: uuid.UUID


class ReviewQueueItem(BaseModel):
    submission_id: uuid.UUID
    attempt_number: int
    submitted_at: datetime
    intern_name: str
    task_title: str
    cohort_name: str
    rubric_version_id: uuid.UUID


class ReviewRubric(BaseModel):
    id: uuid.UUID
    version: int
    content: dict[str, Any]
