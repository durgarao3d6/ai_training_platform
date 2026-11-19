import uuid

from pydantic import BaseModel


class DashboardTaskOut(BaseModel):
    task_instance_id: uuid.UUID
    task_template_id: uuid.UUID
    title: str
    status: str


class MilestoneStatusOut(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    position: int
    status: str  # locked | unlocked | complete
    reason: str  # plain-language explanation, e.g. what unlocks a locked milestone (FR-INT-02)
    tasks: list[DashboardTaskOut]


class CurrentTaskOut(BaseModel):
    task_instance_id: uuid.UUID
    title: str
    milestone_title: str
    status: str


class EnrollmentDashboardOut(BaseModel):
    enrollment_id: uuid.UUID
    course_id: uuid.UUID
    course_title: str
    role_profile: str
    cohort_name: str
    trainer_name: str | None
    milestones: list[MilestoneStatusOut]
    current: CurrentTaskOut | None


class InternDashboardOut(BaseModel):
    intern_id: uuid.UUID
    full_name: str
    enrollments: list[EnrollmentDashboardOut]
