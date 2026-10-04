import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import StarSource

# 2026-10-03 新增摘星阁（M7）模块：零散语句/想法/备忘录。（单表，够用就不拆）
#
# 与世势洞察三张表的关键差异：本表【必带 user_id】。新闻源与日报是全局内容型
# 资源（见 docs/design/phases/M6.md 5-2），而星星是最私人的数据——一个人的
# 念头、没写完的话，绝不与第二个人共享，也不进任何定时任务。宁可多一个 where。
#
# preview 列是刻意冗余：星图一次要 250 条摘要，写入时算一次存 varchar(80)，
# 读时是纯定长列，且前端拿到的截断长度永远一致（不会这条 78 字那条 82 字）。
#
# origin_ref 是跨模块软引用，【不加外键】：硬外键会让「删一篇日报」连带引爆
# 本表，也会把 news→stars 的依赖方向焊死（Card.source_concept_id 的存废史即教训）。


def _star_source_enum() -> Enum:
    """2026-10-03 与 news.py 的 _news_domain_enum() 同一处理：SQLAlchemy 的 Enum
    默认按「成员名」读写，而 StarSource 成员名（MANUAL）与值（manual）大小写不一致，
    不指定 values_callable 会在读行时报 LookupError。库里的列是 VARCHAR，数据是小写值。"""
    return Enum(
        StarSource,
        native_enum=False,
        values_callable=lambda cls: [m.value for m in cls],
    )


class Star(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "stars"
    # 2026-10-03 复合索引必须在模型上用 __table_args__ 声明一遍，与迁移保持一致：
    # 只在迁移里创建的话，下次 alembic autogenerate 会认为它是"多余索引"并 drop。
    # ix_stars_tags_gin 走 GIN，无法用标准 Index 表达，只在迁移里维护
    # （迁移文件里已注明，改动时需人工同步）。
    __table_args__ = (
        Index("ix_stars_user_archived_created", "user_id", "is_archived", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 正文上限由 schema 的 Field(max_length=5000) 兜住，DB 侧 text 不设限
    content: Mapped[str] = mapped_column(Text, nullable=False)
    preview: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[StarSource] = mapped_column(
        _star_source_enum(), nullable=False, server_default="manual"
    )
    origin_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # ['灵感', '英语']。用 JSONB + GIN 索引而非关联表：单用户个人标签量级在几十个，
    # jsonb @> 走 GIN 索引与关联表同数量级，却省两张表和一个 join。
    # 代价：标签不能改名（v1 一并不做改名）。升级路径见 docs/design/phases/M7.md。
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False, server_default="[]")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 归档 = 流星划过后的安息处，默认查询一律排除，不等于删除
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 最近一次被"抓住"（打开详情）的时刻，v1 只写不读，为「最常回味的星」预留
    last_grabbed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
