"""add news tracking (M6 world insight)

Revision ID: b2c4d6e8f0a1
Revises: a1c4e9f06b23
Create Date: 2026-10-03 16:00:00

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c4d6e8f0a1"
down_revision: str | Sequence[str] | None = "a1c4e9f06b23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# 2026-10-03 世势洞察（M6）预置新闻源。全部上线前经 curl 实测 200 且返回合法 RSS/Atom；
# 中国网络不通的站点（BBC / Economist / Google News / Reddit 等）未收录，
# 需要时可在页面「来源管理」里补，RSSHub 路由同样支持。
DEFAULT_NEWS_SOURCES: tuple[tuple[str, str, str], ...] = (
    # (名称, URL, 板块)
    ("OpenAI News", "https://openai.com/news/rss.xml", "ai"),
    ("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml", "ai"),
    ("Google The Keyword", "https://blog.google/rss/", "ai"),
    ("IEEE Spectrum · AI", "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss", "ai"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "tech"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "tech"),
    ("TechCrunch", "https://techcrunch.com/feed/", "tech"),
    ("Solidot", "https://www.solidot.org/index.rss", "tech"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "tech"),
    ("CNBC Finance", "https://www.cnbc.com/id/10000664/device/rss/rss.html", "finance"),
    ("Fortune", "https://fortune.com/feed/", "finance"),
    ("MIT News", "https://news.mit.edu/rss/research", "education"),
    ("Inside Higher Ed", "https://www.insidehighered.com/rss.xml", "education"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml", "world"),
    ("France 24 (EN)", "https://www.france24.com/en/rss", "world"),
    ("NPR News", "https://feeds.npr.org/1001/rss.xml", "general"),
    ("ABC News Top Stories", "https://feeds.abcnews.com/abcnews/topstories", "general"),
)


def upgrade() -> None:
    op.create_table(
        "news_sources",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column(
            "domain",
            # 2026-10-03 values_callable：SQLAlchemy 默认按成员名映射，NewsDomain
            # 成员名（AI）与值（ai）大小写不一致，需显式按值映射，否则读行报 LookupError
            sa.Enum(
                "ai", "tech", "finance", "education", "world", "general",
                name="newsdomain",
                native_enum=False,
                values_callable=lambda cls: list(cls),
            ),
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=200), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_news_sources_domain"), "news_sources", ["domain"], unique=False
    )

    op.create_table(
        "news_articles",
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column(
            "domain",
            # 2026-10-03 values_callable：SQLAlchemy 默认按成员名映射，NewsDomain
            # 成员名（AI）与值（ai）大小写不一致，需显式按值映射，否则读行报 LookupError
            sa.Enum(
                "ai", "tech", "finance", "education", "world", "general",
                name="newsdomain",
                native_enum=False,
                values_callable=lambda cls: list(cls),
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["source_id"], ["news_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # 指纹唯一 = 去重约束，同一链接跨源重复都不会二次入库
        sa.UniqueConstraint("fingerprint", name="uq_news_articles_fingerprint"),
    )
    op.create_index(
        op.f("ix_news_articles_source_id"), "news_articles", ["source_id"], unique=False
    )
    op.create_index(
        op.f("ix_news_articles_domain"), "news_articles", ["domain"], unique=False
    )
    op.create_index(
        op.f("ix_news_articles_published_at"),
        "news_articles",
        ["published_at"],
        unique=False,
    )

    op.create_table(
        "news_digests",
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column(
            "domain",
            # 2026-10-03 values_callable：SQLAlchemy 默认按成员名映射，NewsDomain
            # 成员名（AI）与值（ai）大小写不一致，需显式按值映射，否则读行报 LookupError
            sa.Enum(
                "ai", "tech", "finance", "education", "world", "general",
                name="newsdomain",
                native_enum=False,
                values_callable=lambda cls: list(cls),
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "items",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("article_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("degraded", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        # (日期, 板块) 唯一：重复生成日报是覆盖而不是新增行
        sa.UniqueConstraint("digest_date", "domain", name="uq_news_digests_date_domain"),
    )
    op.create_index(
        op.f("ix_news_digests_digest_date"), "news_digests", ["digest_date"], unique=False
    )
    op.create_index(
        op.f("ix_news_digests_domain"), "news_digests", ["domain"], unique=False
    )

    op.bulk_insert(
        sa.table(
            "news_sources",
            sa.column("id", sa.UUID()),
            sa.column("name", sa.String),
            sa.column("url", sa.String),
            sa.column("domain", sa.String),
            sa.column("is_enabled", sa.Boolean),
        ),
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "url": url,
                "domain": domain,
                "is_enabled": True,
            }
            for name, url, domain in DEFAULT_NEWS_SOURCES
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_news_digests_domain"), table_name="news_digests")
    op.drop_index(op.f("ix_news_digests_digest_date"), table_name="news_digests")
    op.drop_table("news_digests")
    op.drop_index(op.f("ix_news_articles_published_at"), table_name="news_articles")
    op.drop_index(op.f("ix_news_articles_domain"), table_name="news_articles")
    op.drop_index(op.f("ix_news_articles_source_id"), table_name="news_articles")
    op.drop_table("news_articles")
    op.drop_index(op.f("ix_news_sources_domain"), table_name="news_sources")
    op.drop_table("news_sources")
