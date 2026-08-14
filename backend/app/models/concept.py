import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ConceptRelationType, Domain

# text-embedding-3-small 输出维度
EMBEDDING_DIM = 1536


class ConceptNode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "concept_nodes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capture_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("captures.id", ondelete="SET NULL"), index=True
    )
    domain: Mapped[Domain] = mapped_column(Enum(Domain, native_enum=False), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    capture: Mapped["Capture"] = relationship(back_populates="concept_nodes")
    cards: Mapped[list["Card"]] = relationship(back_populates="source_concept")
    outgoing_edges: Mapped[list["ConceptEdge"]] = relationship(
        foreign_keys="ConceptEdge.source_id", back_populates="source", cascade="all, delete-orphan"
    )
    incoming_edges: Mapped[list["ConceptEdge"]] = relationship(
        foreign_keys="ConceptEdge.target_id", back_populates="target", cascade="all, delete-orphan"
    )


class ConceptEdge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "concept_edges"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concept_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[ConceptRelationType] = mapped_column(Enum(ConceptRelationType, native_enum=False), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_ai_generated: Mapped[bool] = mapped_column(default=True)

    source: Mapped["ConceptNode"] = relationship(foreign_keys=[source_id], back_populates="outgoing_edges")
    target: Mapped["ConceptNode"] = relationship(foreign_keys=[target_id], back_populates="incoming_edges")
