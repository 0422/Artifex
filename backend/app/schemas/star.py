import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StarRange, StarSource

# 2026-10-03 新增摘星阁（M7）模块的序列化 schema。
# 命名沿用房子习惯：*Create 输入 / *Update 局部更新 / *Read 输出 / *Brief 列表摘要 / *Page 分页。
# 注意：id 一律声明 uuid.UUID 而非 str——ORM 实例给的是 UUID 对象，Pydantic v2 不会把它
# lax 转成 str（news schema 上踩出过 500，见 schemas/news.py:10-14）。

# 单颗星星的正文上限。DB 侧是 text 不设限，约束放这里：星空只展示 preview，
# 但抽屉里要能读完一整段长念头，5000 字足够且不至于把接口打成传输入口。
MAX_CONTENT_CHARS = 5000
# 列表摘要长度。星图一次要 200+ 条，定长截断保证前端渲染稳定、响应体可控。
PREVIEW_CHARS = 80
# 单颗星最多挂多少个标签。再多就等于没分类，且标签 chip 会挤爆筛选栏。
MAX_TAGS_PER_STAR = 20
MAX_TAG_CHARS = 30


def normalize_tags(tags: list[str]) -> list[str]:
    """2026-10-03 标签归一化：去空白、去重、丢空串、截断单标签长度。

    顺序保留用户输入次序（首个标签即"主标签"，前端排在最前）。
    不加小写折叠：中文标签没有大小写问题，英文标签用户可能真的想区分 Idea 与 idea。
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw in tags:
        name = raw.strip()[:MAX_TAG_CHARS].strip()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result[:MAX_TAGS_PER_STAR]


class StarCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_STAR)
    is_pinned: bool = False
    is_favorite: bool = False
    # 2026-10-03 跨模块转存（世势洞察日报 / 情境对话 → 星）由调用方带上来源与出处。
    # 默认 manual 让老调用方无感；source 限枚举，origin_ref 是裸 uuid 软引用
    # （见 models/star.py：不加外键，避免跨模块依赖焊死）
    source: StarSource = StarSource.MANUAL
    origin_ref: uuid.UUID | None = None


class StarUpdate(BaseModel):
    """局部更新：置顶/收藏/归档的开关各传一个布尔即可，不必回传整个对象。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    content: str | None = Field(default=None, min_length=1, max_length=MAX_CONTENT_CHARS)
    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_STAR)
    is_pinned: bool | None = None
    is_favorite: bool | None = None
    is_archived: bool | None = None


class StarBrief(BaseModel):
    """星图列表项：只给 preview，不给 content。

    这是「列表轻、详情按需」节奏的落点——与 NewsDigestListItem 不回报 items 同理
    （docs/design/phases/M6.md）。200 颗星若各带 5000 字正文，一次响应就是 MB 级，
    而星图上每颗星只需要 80 字。
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    preview: str
    source: StarSource
    tags: list[str] = Field(default_factory=list)
    is_pinned: bool
    is_favorite: bool
    created_at: datetime


class StarRead(BaseModel):
    """详情：全文 + 归档状态 + 更新时间（编辑过的星要在抽屉里露出"改于"）。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    preview: str
    source: StarSource
    origin_ref: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)
    is_pinned: bool
    is_favorite: bool
    is_archived: bool
    last_grabbed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StarPage(BaseModel):
    items: list[StarBrief]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)


class StarTagCount(BaseModel):
    name: str
    count: int = Field(ge=0)


class StarRandomRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=20)


class StarImportRequest(BaseModel):
    """批量导入：一行一颗星。纯空白行与批次内重复行由 service 跳过并计入 skipped。"""

    lines: list[str] = Field(min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_STAR)


class StarImportResult(BaseModel):
    created: int
    skipped: int
