"""add scenario cards

Revision ID: 9c42d8e6a1f0
Revises: f714d5b82b08
Create Date: 2026-08-14 20:30:00

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c42d8e6a1f0"
down_revision: str | Sequence[str] | None = "f714d5b82b08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEED_SCENARIOS = (
    ("餐厅点餐", "在餐厅阅读菜单、询问菜品并完成点餐。", "JA", "N4"),
    ("便利店购物", "在便利店寻找商品、询问价格并完成结账。", "JA", "N5"),
    ("问路", "向路人询问目的地并确认路线和交通方式。", "JA", "N4"),
    ("自我介绍", "介绍自己的背景、兴趣、学习目标并回应追问。", "JA", "N4"),
    ("商务会议", "在会议中表达观点、确认信息并协商下一步行动。", "JA", "N3"),
)


def upgrade() -> None:
    op.alter_column(
        "chat_sessions",
        "ended_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="ended_at AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )

    scenario_cards = op.create_table(
        "scenario_cards",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "language",
            sa.Enum("EN", "JA", name="scenariolanguage", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "difficulty",
            sa.Enum(
                "A1",
                "A2",
                "B1",
                "B2",
                "C1",
                "C2",
                "N5",
                "N4",
                "N3",
                "N2",
                "N1",
                name="scenariodifficulty",
                native_enum=False,
            ),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scenario_cards_user_id"), "scenario_cards", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_scenario_cards_is_active"),
        "scenario_cards",
        ["is_active"],
        unique=False,
    )

    op.add_column("chat_sessions", sa.Column("scenario_id", sa.UUID(), nullable=True))
    op.create_index(
        op.f("ix_chat_sessions_scenario_id"),
        "chat_sessions",
        ["scenario_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_chat_sessions_scenario_id_scenario_cards",
        "chat_sessions",
        "scenario_cards",
        ["scenario_id"],
        ["id"],
        ondelete="SET NULL",
    )

    connection = op.get_bind()
    user_ids = connection.execute(sa.text("SELECT id FROM users")).scalars().all()
    if user_ids:
        op.bulk_insert(
            scenario_cards,
            [
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "title": title,
                    "description": description,
                    "language": language,
                    "difficulty": difficulty,
                    "is_active": True,
                }
                for user_id in user_ids
                for title, description, language, difficulty in SEED_SCENARIOS
            ],
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_chat_sessions_scenario_id_scenario_cards",
        "chat_sessions",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_chat_sessions_scenario_id"), table_name="chat_sessions")
    op.drop_column("chat_sessions", "scenario_id")
    op.drop_index(op.f("ix_scenario_cards_is_active"), table_name="scenario_cards")
    op.drop_index(op.f("ix_scenario_cards_user_id"), table_name="scenario_cards")
    op.drop_table("scenario_cards")
    op.alter_column(
        "chat_sessions",
        "ended_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="ended_at AT TIME ZONE 'UTC'",
        existing_nullable=True,
    )
