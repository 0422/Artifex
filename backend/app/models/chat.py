import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ChatMessageRole, ChatSessionStatus

if TYPE_CHECKING:
    from app.models.scenario import ScenarioCard


class ChatSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenario_cards.id", ondelete="SET NULL"),
        index=True,
    )
    # Keep the title snapshot so history remains stable after a scenario is renamed or deactivated.
    scenario: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[ChatSessionStatus] = mapped_column(
        Enum(ChatSessionStatus, native_enum=False),
        default=ChatSessionStatus.ACTIVE,
        nullable=False,
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[dict | None] = mapped_column(JSONB)  # summary / weak_points / score
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    scenario_card: Mapped["ScenarioCard | None"] = relationship(
        back_populates="sessions"
    )


class ChatMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ChatMessageRole] = mapped_column(
        Enum(ChatMessageRole, native_enum=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    correction: Mapped[dict | None] = mapped_column(JSONB)
    audio_url: Mapped[str | None] = mapped_column(String(500))

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
