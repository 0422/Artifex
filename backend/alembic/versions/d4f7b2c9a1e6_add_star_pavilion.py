"""add star pavilion (M7 fleeting notes)

Revision ID: d4f7b2c9a1e6
Revises: b2c4d6e8f0a1
Create Date: 2026-10-03 22:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4f7b2c9a1e6"
down_revision: str | Sequence[str] | None = "b2c4d6e8f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stars",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # preview 是刻意冗余的摘要列（80 字），写入时算好，星图列表读时零成本
        sa.Column("preview", sa.String(length=80), nullable=False),
        # source/origin_ref 为跨模块转存预留，v1 只写 manual/import
        sa.Column(
            "source",
            sa.Enum(
                "manual", "import", "news", "chat",
                name="starsource",
                native_enum=False,
                values_callable=lambda cls: list(cls),
            ),
            server_default="manual",
            nullable=False,
        ),
        sa.Column("origin_ref", sa.UUID(), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("last_grabbed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    # 主查询路径：某人的、未归档的、按时间倒序（list_stars 的 base filter + order）
    # 注意：此索引已在 models/star.py 的 __table_args__ 中同步声明，
    # 否则下次 alembic autogenerate 会判定为多余索引并 drop 掉。
    # ix_stars_tags_gin 走 GIN，标准 Index 表达不了，只在本迁移中维护，需人工同步。
    op.create_index(
        op.f("ix_stars_user_id"), "stars", ["user_id"], unique=False
    )
    op.create_index(
        "ix_stars_user_archived_created",
        "stars",
        ["user_id", "is_archived", sa.text("created_at DESC")],
        unique=False,
    )
    # 标签筛选走 jsonb @>，需要 GIN 索引才不退化成全表扫描
    op.create_index(
        "ix_stars_tags_gin", "stars", ["tags"], unique=False, postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_stars_tags_gin", table_name="stars")
    op.drop_index("ix_stars_user_archived_created", table_name="stars")
    op.drop_index(op.f("ix_stars_user_id"), table_name="stars")
    op.drop_table("stars")
