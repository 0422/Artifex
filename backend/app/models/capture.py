import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import CaptureSourceType, CaptureStatus, Domain


class Capture(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "captures"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[Domain] = mapped_column(Enum(Domain, native_enum=False), nullable=False)
    source_type: Mapped[CaptureSourceType] = mapped_column(Enum(CaptureSourceType, native_enum=False), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    raw_content: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CaptureStatus] = mapped_column(
        Enum(CaptureStatus, native_enum=False), default=CaptureStatus.PENDING, nullable=False
    )

    concept_nodes: Mapped[list["ConceptNode"]] = relationship(back_populates="capture", cascade="all, delete-orphan")
