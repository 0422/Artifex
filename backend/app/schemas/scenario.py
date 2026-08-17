import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ScenarioDifficulty, ScenarioLanguage


class ScenarioCategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    domain: str
    parent_id: uuid.UUID | None = None


def normalize_tags(tags: list[str]) -> list[str]:
    normalized = []
    for tag in tags:
        clean = tag.strip()
        if clean and clean not in normalized:
            normalized.append(clean[:30])
    return normalized


class ScenarioCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    language: ScenarioLanguage
    difficulty: ScenarioDifficulty
    domain: str = Field(default="language", min_length=1, max_length=50)
    scenario_mode: Literal[
        "role_play",
        "guided_discussion",
        "socratic_dialogue",
        "debate",
        "source_analysis",
        "work_analysis",
    ] = "role_play"
    estimated_minutes: int | None = Field(default=None, ge=1, le=240)
    tags: list[str] = Field(default_factory=list, max_length=20)
    category_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)

    @field_validator("tags")
    @classmethod
    def normalize_tags_field(cls, tags: list[str]) -> list[str]:
        return normalize_tags(tags)


class ScenarioUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    language: ScenarioLanguage | None = None
    difficulty: ScenarioDifficulty | None = None
    domain: str | None = Field(default=None, min_length=1, max_length=50)
    scenario_mode: (
        Literal[
            "role_play",
            "guided_discussion",
            "socratic_dialogue",
            "debate",
            "source_analysis",
            "work_analysis",
        ]
        | None
    ) = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=240)
    tags: list[str] | None = Field(default=None, max_length=20)
    category_ids: list[uuid.UUID] | None = Field(default=None, max_length=20)

    @field_validator("tags")
    @classmethod
    def normalize_optional_tags(cls, tags: list[str] | None) -> list[str] | None:
        return normalize_tags(tags) if tags is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "ScenarioUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个要修改的字段")
        nullable_fields = {"estimated_minutes"}
        if any(
            getattr(self, field) is None
            for field in self.model_fields_set - nullable_fields
        ):
            raise ValueError("修改字段不能为 null")
        return self


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    language: ScenarioLanguage
    difficulty: ScenarioDifficulty
    domain: str = "language"
    scenario_mode: str = "role_play"
    estimated_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    categories: list[ScenarioCategoryBrief] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime
