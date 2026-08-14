import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CaptureSourceType, CaptureStatus, Domain


class CaptureCreateRequest(BaseModel):
    domain: Domain
    source_type: CaptureSourceType
    # text 类型填 content；url 类型填 source_url；pdf 类型走 multipart 上传（见路由）
    content: str | None = None
    source_url: str | None = None


class ConceptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    definition: str | None
    domain: Domain


class RelatedConceptRead(BaseModel):
    id: uuid.UUID
    label: str


class ConceptWithRelations(ConceptRead):
    related: list[RelatedConceptRead] = []
    card_count: int = 0


class CaptureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: Domain
    source_type: CaptureSourceType
    source_url: str | None
    summary: str | None
    status: CaptureStatus
    created_at: datetime


class CaptureConceptsResponse(BaseModel):
    capture: CaptureRead
    concepts: list[ConceptWithRelations]
