import uuid

from pydantic import BaseModel

from app.modules.catalog.schemas import TaskTemplateOut


class TaskInstanceOut(BaseModel):
    id: uuid.UUID
    status: str
    enrollment_id: uuid.UUID
    task: TaskTemplateOut
