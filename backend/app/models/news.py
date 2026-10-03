import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import NewsDomain

# 2026-10-03 世势洞察（M6）模块的三张表，构成「订阅源 → 原始文章 → LLM 日报」管线：
#   news_sources   用户维护的 RSS 源（迁移里带约 15 个预置源）
#   news_articles  抓取落库的原始文章，URL 指纹去重，是日报的素材池
#   news_digests   LLM 按板块每日生成的策展结果，(digest_date, domain) 唯一，支持幂等重生成
# 三张表都不带 user_id：源与日报都是全局内容型资源（区别于 learning_events / edge_devices
# 这类个人数据），定时任务也无需按用户分片。
__all__ = ["NewsArticle", "NewsDigest", "NewsSource"]


def _news_domain_enum() -> Enum:
    """2026-10-03 修复：SQLAlchemy 的 Enum 默认按「成员名」读写，而 NewsDomain 的
    成员名（AI/TECH）与值（ai/tech）大小写不一致——库里存的是小写值，不指定
    values_callable 会在读行时报 LookupError: 'ai' is not among the defined enum
    values。这里显式按值映射，与库里的小写数据和前端类型对齐。"""
    return Enum(NewsDomain, native_enum=False, values_callable=lambda cls: [m.value for m in cls])


class NewsSource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "news_sources"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    domain: Mapped[NewsDomain] = mapped_column(
        _news_domain_enum(), nullable=False, index=True
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # 抓取状态由 fetch_source 维护：成功刷新 last_fetched_at 并清空 last_error，
    # 失败写 last_error（截断 200 字）供前端展示，不阻断其余源的抓取
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(200), nullable=True)

    articles: Mapped[list["NewsArticle"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class NewsArticle(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "news_articles"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("news_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # domain 从 source 冗余一份：按板块取素材时免 join，源改板块也不影响已抓文章
    domain: Mapped[NewsDomain] = mapped_column(_news_domain_enum(), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    # sha1(normalized url)，unique 索引即去重约束，同一源或跨源重复链接都不会二次入库
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # 摘要截断存储（约 300 字），只作 LLM 输入，不做全文镜像
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    source: Mapped["NewsSource"] = relationship(back_populates="articles")


class NewsDigest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "news_digests"
    # 2026-10-03 (digest_date, domain) 唯一约束是幂等重生成的基础：
    # generate_digest 对已存在的当日同板块日报做覆盖更新，不累积重复行
    __table_args__ = (UniqueConstraint("digest_date", "domain", name="uq_news_digests_date_domain"),)

    digest_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    domain: Mapped[NewsDomain] = mapped_column(_news_domain_enum(), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # LLM 策展结果：[{headline, summary_zh, why_matters, importance, url, source_name, published_at}]
    # items 存 JSONB 而非外键关联：展示层一次读全，且 LLM 输出本就带 url/source_name
    items: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False, server_default="[]")
    article_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # degraded=True 表示 LLM 调用失败/输出不合法时的降级稿：items 退化为原始标题列表
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
