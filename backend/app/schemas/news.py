import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import NewsDomain
from app.models.news import NewsArticle

# 2026-10-03 新增世势洞察（M6）模块的序列化 schema。
# 命名沿用房子习惯：*Create 输入 / *Update 局部更新 / *Read 输出 / *Page 分页。
# 注意：id/source_id 用 uuid.UUID 而非 str——ORM 实例给的是 UUID 对象，
# Pydantic v2 不会把 UUID lax 转成 str（之前踩过：model_validate 直接 ValidationError），
# 序列化成 JSON 时 FastAPI 自动转字符串，前端拿到的仍是 string。


class NewsSourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=500)
    domain: NewsDomain


class NewsSourceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    domain: NewsDomain | None = None
    is_enabled: bool | None = None


class NewsSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    url: str
    domain: NewsDomain
    is_enabled: bool
    last_fetched_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class NewsArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    domain: NewsDomain
    title: str
    url: str
    excerpt: str | None
    published_at: datetime | None
    created_at: datetime
    # 来源名是冗余展示字段：articles 查询都带 selectinload(NewsArticle.source)，
    # 由 before 校验器从关系里取出，避免前端为拿一个名字再发一次请求
    source_name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _attach_source_name(cls, data: Any) -> Any:
        if isinstance(data, NewsArticle):
            values = {
                field: getattr(data, field)
                for field in ("id", "source_id", "domain", "title", "url", "excerpt", "published_at", "created_at")
            }
            values["source_name"] = data.source.name if data.source else ""
            return values
        return data


class NewsDigestItem(BaseModel):
    headline: str = Field(min_length=1)
    summary_zh: str = ""
    why_matters: str = ""
    # float 而非 int：LLM 偶尔输出 8.5 这类分值，卡 int 会把整份日报打进修降级路径
    importance: float = Field(default=5.0, ge=0, le=10)
    url: str = ""
    source_name: str = ""
    published_at: datetime | None = None


class NewsDigestContent(BaseModel):
    """LLM 日报输出的校验模型，generate_digest 用它把原始 dict 收敛成可信结构。"""

    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    items: list[NewsDigestItem] = Field(default_factory=list)


class NewsDigestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    digest_date: date
    domain: NewsDomain
    title: str
    summary: str
    items: list[NewsDigestItem] = Field(default_factory=list)
    article_count: int
    degraded: bool
    created_at: datetime


class NewsDigestListItem(BaseModel):
    """列表页不回报 items，避免翻页时把 40 条策展结果全拉下来。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    digest_date: date
    domain: NewsDomain
    title: str
    article_count: int
    degraded: bool
    created_at: datetime


class NewsDigestPage(BaseModel):
    items: list[NewsDigestListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class NewsArticlePage(BaseModel):
    items: list[NewsArticleRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class NewsFetchResult(BaseModel):
    total_sources: int
    succeeded: int
    failed: int
    new_articles: int


class NewsDigestGenerateRequest(BaseModel):
    # 不传 domain 表示六个板块各生成一份；digest_date 缺省为今天（固定 UTC+8）
    domain: NewsDomain | None = None
    digest_date: date | None = None
