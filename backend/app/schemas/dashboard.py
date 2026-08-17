import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.report import SessionReport

ReportStatus = Literal["ready", "degraded", "insufficient_data", "missing", "invalid"]


class ScenarioDistributionItem(BaseModel):
    scenario_id: uuid.UUID | None
    title: str
    count: int = Field(ge=1)


class WeakPointFrequency(BaseModel):
    tag: str
    category: str
    count: int = Field(ge=1)


class DashboardOverview(BaseModel):
    total_conversations: int = Field(ge=0)
    total_duration_seconds: int = Field(ge=0)
    scored_conversations: int = Field(ge=0)
    average_performance_score: float | None = Field(default=None, ge=0, le=100)
    scenario_distribution: list[ScenarioDistributionItem]
    frequent_weak_points: list[WeakPointFrequency]


class DashboardSessionItem(BaseModel):
    id: uuid.UUID
    scenario_id: uuid.UUID | None
    scenario_title: str
    language: str
    difficulty: str | None
    duration_seconds: int
    performance_score: int | None
    weak_points_count: int
    report_status: ReportStatus
    created_at: datetime
    ended_at: datetime | None


class DashboardSessionPage(BaseModel):
    items: list[DashboardSessionItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class DashboardSessionDetail(DashboardSessionItem):
    report: SessionReport | None
