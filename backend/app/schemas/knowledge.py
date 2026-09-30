import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KnowledgeCategoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    domain: str = Field(default="custom", min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class KnowledgeCategoryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    domain: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class KnowledgeCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    domain: str
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # 2026-09-30 归属只参与 is_shared 计算，不回传给前端，避免暴露"这条是谁建的"
    user_id: uuid.UUID | None = Field(default=None, exclude=True)
    # 官方共享分类（雅思真题库）为 True：前端据此隐藏编辑/删除入口
    is_shared: bool = False

    @model_validator(mode="after")
    def _derive_is_shared(self) -> "KnowledgeCategoryRead":
        self.is_shared = self.user_id is None
        return self


class KnowledgeCategoryTree(KnowledgeCategoryRead):
    children: list["KnowledgeCategoryTree"] = Field(default_factory=list)
    card_count: int = 0


KnowledgeCategoryTree.model_rebuild()
