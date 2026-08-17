"""add knowledge library

Revision ID: 4d8b72f1c9aa
Revises: 9c42d8e6a1f0
Create Date: 2026-08-16 10:00:00

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "4d8b72f1c9aa"
down_revision: str | Sequence[str] | None = "9c42d8e6a1f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_CATEGORY_TREE = (
    ("语言", "language", ("英语", "日语", "韩语")),
    ("历史", "history", ("中国古代", "中国近现代", "世界历史")),
    ("政治", "politics", ("政治制度", "政治思想", "国际关系")),
    ("艺术", "art", ("绘画", "建筑", "表演艺术")),
    ("电影", "film", ("类型研究", "导演与作品", "视听语言")),
)


def upgrade() -> None:
    op.add_column(
        "scenario_cards",
        sa.Column(
            "domain", sa.String(length=50), server_default="language", nullable=False
        ),
    )
    op.add_column(
        "scenario_cards",
        sa.Column(
            "scenario_mode",
            sa.String(length=40),
            server_default="role_play",
            nullable=False,
        ),
    )
    op.add_column(
        "scenario_cards", sa.Column("estimated_minutes", sa.Integer(), nullable=True)
    )
    op.add_column(
        "scenario_cards",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_scenario_cards_domain"), "scenario_cards", ["domain"], unique=False
    )

    categories = op.create_table(
        "knowledge_categories",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=50), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["parent_id"], ["knowledge_categories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_categories_domain"),
        "knowledge_categories",
        ["domain"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_categories_is_active"),
        "knowledge_categories",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_categories_parent_id"),
        "knowledge_categories",
        ["parent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_categories_user_id"),
        "knowledge_categories",
        ["user_id"],
        unique=False,
    )

    links = op.create_table(
        "scenario_category_links",
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["knowledge_categories.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"], ["scenario_cards.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("scenario_id", "category_id"),
    )

    connection = op.get_bind()
    user_ids = connection.execute(sa.text("SELECT id FROM users")).scalars().all()
    category_rows = []
    japanese_category_ids: dict[uuid.UUID, uuid.UUID] = {}
    for user_id in user_ids:
        for root_order, (root_name, domain, children) in enumerate(
            DEFAULT_CATEGORY_TREE
        ):
            root_id = uuid.uuid4()
            category_rows.append(
                {
                    "id": root_id,
                    "user_id": user_id,
                    "parent_id": None,
                    "name": root_name,
                    "domain": domain,
                    "sort_order": root_order,
                    "is_active": True,
                }
            )
            for child_order, child_name in enumerate(children):
                child_id = uuid.uuid4()
                category_rows.append(
                    {
                        "id": child_id,
                        "user_id": user_id,
                        "parent_id": root_id,
                        "name": child_name,
                        "domain": domain,
                        "sort_order": child_order,
                        "is_active": True,
                    }
                )
                if domain == "language" and child_name == "日语":
                    japanese_category_ids[user_id] = child_id
    if category_rows:
        op.bulk_insert(categories, category_rows)

    link_rows = []
    for user_id, category_id in japanese_category_ids.items():
        scenario_ids = (
            connection.execute(
                sa.text("SELECT id FROM scenario_cards WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            .scalars()
            .all()
        )
        link_rows.extend(
            {"scenario_id": scenario_id, "category_id": category_id}
            for scenario_id in scenario_ids
        )
    if link_rows:
        op.bulk_insert(links, link_rows)


def downgrade() -> None:
    op.drop_table("scenario_category_links")
    op.drop_index(
        op.f("ix_knowledge_categories_user_id"), table_name="knowledge_categories"
    )
    op.drop_index(
        op.f("ix_knowledge_categories_parent_id"), table_name="knowledge_categories"
    )
    op.drop_index(
        op.f("ix_knowledge_categories_is_active"), table_name="knowledge_categories"
    )
    op.drop_index(
        op.f("ix_knowledge_categories_domain"), table_name="knowledge_categories"
    )
    op.drop_table("knowledge_categories")
    op.drop_index(op.f("ix_scenario_cards_domain"), table_name="scenario_cards")
    op.drop_column("scenario_cards", "tags")
    op.drop_column("scenario_cards", "estimated_minutes")
    op.drop_column("scenario_cards", "scenario_mode")
    op.drop_column("scenario_cards", "domain")
