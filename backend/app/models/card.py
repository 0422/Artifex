import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import CardType, Domain


class Card(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cards"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[Domain] = mapped_column(Enum(Domain, native_enum=False), nullable=False)
    card_type: Mapped[CardType] = mapped_column(Enum(CardType, native_enum=False), nullable=False)
    front_content: Mapped[str] = mapped_column(Text, nullable=False)
    back_content: Mapped[str] = mapped_column(Text, nullable=False)
    source_concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concept_nodes.id", ondelete="SET NULL"), index=True
    )

    # FSRS 状态
    fsrs_state: Mapped[dict | None] = mapped_column(JSONB)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)

    # 跨领域去重合并
    is_merged: Mapped[bool] = mapped_column(Boolean, default=False)
    merged_from_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))

    source_concept: Mapped["ConceptNode"] = relationship(back_populates="cards")
    review_logs: Mapped[list["ReviewLog"]] = relationship(back_populates="card", cascade="all, delete-orphan")


class ReviewLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_logs"

    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # FSRS: 1=again 2=hard 3=good 4=easy
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    elapsed_days: Mapped[float] = mapped_column(Float, default=0.0)
    scheduled_days: Mapped[float] = mapped_column(Float, default=0.0)

    card: Mapped["Card"] = relationship(back_populates="review_logs")
