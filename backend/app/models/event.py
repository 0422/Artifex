import uuid

from sqlalchemy import Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import Domain, LearningEventType


class LearningEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "learning_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[Domain] = mapped_column(Enum(Domain, native_enum=False), nullable=False)
    event_type: Mapped[LearningEventType] = mapped_column(Enum(LearningEventType, native_enum=False), nullable=False)
    depth: Mapped[str] = mapped_column(String(20), default="moderate")  # shallow/moderate/deep
    duration_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    meta: Mapped[dict | None] = mapped_column(JSONB)

    user: Mapped["User"] = relationship()
