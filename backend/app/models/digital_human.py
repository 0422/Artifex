import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DigitalHumanConfig(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "digital_human_configs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    vrm_model_url: Mapped[str | None] = mapped_column(String(500))
    voice_provider: Mapped[str] = mapped_column(String(50), default="edge_tts")
    voice_id: Mapped[str | None] = mapped_column(String(100))
    stt_engine: Mapped[str] = mapped_column(String(50), default="web_speech")
    wake_word_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    wake_word: Mapped[str | None] = mapped_column(String(50))
    float_widget_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    expression_intensity: Mapped[float] = mapped_column(Float, default=0.8)
    idle_animation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship()
