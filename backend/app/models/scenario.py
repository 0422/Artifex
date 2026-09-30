import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ScenarioDifficulty, ScenarioLanguage

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.knowledge import KnowledgeCategory


class ScenarioCard(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scenario_cards"

    # 2026-09-30 雅思口语真题库为全局共享：user_id 为空表示官方题库，
    # 所有用户可见但不可改；用户自建场景仍归属本人，行为不变。
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[ScenarioLanguage] = mapped_column(
        Enum(ScenarioLanguage, native_enum=False), nullable=False
    )
    difficulty: Mapped[ScenarioDifficulty] = mapped_column(
        Enum(ScenarioDifficulty, native_enum=False), nullable=False
    )
    domain: Mapped[str] = mapped_column(
        String(50), default="language", nullable=False, index=True
    )
    scenario_mode: Mapped[str] = mapped_column(
        String(40), default="role_play", nullable=False, server_default="role_play"
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 2026-09-30 雅思口语场景库：ielts_part 非空时走雅思专属 prompt 与开场白分支，
    # 分别对应 Part 1 考官追问 / Part 2 题卡独白 / Part 3 抽象追问。
    # cue_card 存 Part 2 的题卡正文，UI 单独展示、prompt 单独注入，不混在 description 里。
    ielts_part: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    cue_card: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False, server_default="[]"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="scenario_card", passive_deletes=True
    )
    categories: Mapped[list["KnowledgeCategory"]] = relationship(
        secondary="scenario_category_links", back_populates="scenarios"
    )
