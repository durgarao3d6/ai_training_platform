"""Submissions API models (FR-SUB-01 to 05)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class UploadSignIn(BaseModel):
    task_instance_id: uuid.UUID
    deliverable_id: str = Field(min_length=1, max_length=100)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=200, pattern=r"^[\w.+-]+/[\w.+-]+$")
    size_bytes: int = Field(gt=0)


class UploadSignOut(BaseModel):
    upload_key: str
    url: str
    fields: dict[str, str]
    expires_in: int
    max_bytes: int


class ArtifactIn(BaseModel):
    deliverable_id: str = Field(min_length=1, max_length=100)
    kind: Literal["file", "link", "text"]
    upload_key: str | None = Field(default=None, max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    text: str | None = None

    @model_validator(mode="after")
    def _one_value(self) -> "ArtifactIn":
        expected = {"file": "upload_key", "link": "url", "text": "text"}[self.kind]
        given = [name for name in ("upload_key", "url", "text") if getattr(self, name) is not None]
        if given != [expected]:
            raise ValueError(f"a {self.kind} artifact needs exactly '{expected}'")
        return self


class SubmissionIn(BaseModel):
    artifacts: list[ArtifactIn] = Field(min_length=1, max_length=50)


class ArtifactOut(BaseModel):
    id: uuid.UUID
    deliverable_id: str
    kind: str
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    url: str | None
    text: str | None
    download_path: str | None  # API path for files; downloads are permission-checked


class SubmissionOut(BaseModel):
    id: uuid.UUID
    task_instance_id: uuid.UUID
    attempt_number: int
    status: str
    created_at: datetime
    artifacts: list[ArtifactOut]
    evaluation_id: uuid.UUID | None = None  # set once the evaluation engine exists (Phase 4)


class SubmissionSummaryOut(BaseModel):
    id: uuid.UUID
    attempt_number: int
    status: str
    created_at: datetime
    artifact_count: int


def artifact_problem(deliverable_id: str, message: str) -> dict[str, Any]:
    return {"deliverable_id": deliverable_id, "message": message}
