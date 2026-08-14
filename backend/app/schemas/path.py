import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Domain, LearningPathStatus, PathMilestoneStatus


class OnboardingQuestion(BaseModel):
    key: str
    question: str
    hint: str | None = None


class OnboardingCompleteRequest(BaseModel):
    domain: Domain
    # 引导收集到的自由格式答案（goal/level/daily_minutes/motivation 等）
    answers: dict


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_index: int
    title: str
    description: str | None
    status: PathMilestoneStatus
    progress_data: dict | None


class LearningPathRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: Domain
    title: str
    starting_point_report: dict | None
    status: LearningPathStatus
    created_at: datetime
    milestones: list[MilestoneRead]
