import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import Domain, LearningPathStatus, PathMilestoneStatus


class LearningPath(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "learning_paths"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[Domain] = mapped_column(Enum(Domain, native_enum=False), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    starting_point_report: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[LearningPathStatus] = mapped_column(
        Enum(LearningPathStatus, native_enum=False), default=LearningPathStatus.ACTIVE, nullable=False
    )

    milestones: Mapped[list["PathMilestone"]] = relationship(
        back_populates="path", cascade="all, delete-orphan", order_by="PathMilestone.order_index"
    )


class PathMilestone(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "path_milestones"

    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PathMilestoneStatus] = mapped_column(
        Enum(PathMilestoneStatus, native_enum=False), default=PathMilestoneStatus.LOCKED, nullable=False
    )
    progress_data: Mapped[dict | None] = mapped_column(JSONB)  # 完成率/正确率等统计

    path: Mapped["LearningPath"] = relationship(back_populates="milestones")
