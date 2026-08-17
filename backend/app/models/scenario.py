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

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
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
