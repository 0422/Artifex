import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.scenario import ScenarioCard


scenario_category_links = Table(
    "scenario_category_links",
    Base.metadata,
    Column(
        "scenario_id",
        UUID(as_uuid=True),
        ForeignKey("scenario_cards.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("knowledge_categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class KnowledgeCategory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_categories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(
        String(50), default="custom", nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    parent: Mapped["KnowledgeCategory | None"] = relationship(
        remote_side="KnowledgeCategory.id", back_populates="children"
    )
    children: Mapped[list["KnowledgeCategory"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="KnowledgeCategory.sort_order",
    )
    scenarios: Mapped[list["ScenarioCard"]] = relationship(
        secondary=scenario_category_links, back_populates="categories"
    )
