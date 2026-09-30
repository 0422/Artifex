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


# 2026-09-30 难度不再由用户选：新建时不渲染该控件，未提供时按输出语言取一个
# 合理默认（CEFR/JLPT/通用三套量纲不同，只能按语言分派）。
_DEFAULT_DIFFICULTY_BY_LANGUAGE = {
    ScenarioLanguage.EN: ScenarioDifficulty.B1,
    ScenarioLanguage.JA: ScenarioDifficulty.N4,
    ScenarioLanguage.ZH: ScenarioDifficulty.INTERMEDIATE,
}


class ScenarioCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    language: ScenarioLanguage
    # 2026-09-30 改为可选：新建界面不再让用户选难度，未提供则按语言推默认值
    difficulty: ScenarioDifficulty | None = None
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
    # 2026-09-30 雅思口语场景库：part 非空即视为雅思场景，走专属 prompt 分支
    ielts_part: int | None = Field(default=None, ge=1, le=3)
    cue_card: str | None = Field(default=None, max_length=2000)

    @field_validator("tags")
    @classmethod
    def normalize_tags_field(cls, tags: list[str]) -> list[str]:
        return normalize_tags(tags)

    @model_validator(mode="after")
    def _fill_default_difficulty(self) -> "ScenarioCreate":
        if self.difficulty is None:
            self.difficulty = _DEFAULT_DIFFICULTY_BY_LANGUAGE[self.language]
        return self


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
    # 2026-09-30 雅思口语场景库：与 Create 一致，允许把场景在雅思/非雅思间切换
    ielts_part: int | None = Field(default=None, ge=1, le=3)
    cue_card: str | None = Field(default=None, max_length=2000)

    @field_validator("tags")
    @classmethod
    def normalize_optional_tags(cls, tags: list[str] | None) -> list[str] | None:
        return normalize_tags(tags) if tags is not None else None

    @model_validator(mode="after")
    def require_change(self) -> "ScenarioUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个要修改的字段")
        # 2026-09-30 雅思字段与难度都允许显式置 null：前者用于在雅思/非雅思间切换，
        # 后者让编辑时也能清掉难度（虽然新建已不再收集难度）
        nullable_fields = {
            "estimated_minutes",
            "ielts_part",
            "cue_card",
            "difficulty",
        }
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
    # 2026-09-30 雅思口语场景库：part 非空即雅思场景，前端据此显示 Part 徽章与 Part 2 题卡
    ielts_part: int | None = None
    cue_card: str | None = None
    # 归属只参与 is_shared 计算，不回传，避免暴露"这条场景是谁建的"
    user_id: uuid.UUID | None = Field(default=None, exclude=True)
    # 官方共享真题为 True：前端据此隐藏编辑/删除入口
    is_shared: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _derive_is_shared(self) -> "ScenarioRead":
        self.is_shared = self.user_id is None
        return self
