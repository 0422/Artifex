import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import CaptureSourceType, Domain
from app.models.user import User
from app.schemas.capture import (
    CaptureConceptsResponse,
    CaptureCreateRequest,
    CaptureRead,
    ConceptWithRelations,
    RelatedConceptRead,
)
from app.services import capture_service
from app.services.content_extractor import (
    ContentExtractionError,
    extract_from_pdf,
    extract_from_text,
    extract_from_url,
)

router = APIRouter(prefix="/capture", tags=["capture"])


async def _resolve_raw_content(payload: CaptureCreateRequest) -> str:
    try:
        if payload.source_type == CaptureSourceType.TEXT:
            return extract_from_text(payload.content or "")
        if payload.source_type == CaptureSourceType.URL:
            if not payload.source_url:
                raise ContentExtractionError("URL 类型必须提供 source_url")
            return await extract_from_url(payload.source_url)
        raise ContentExtractionError("PDF 请使用 /capture/pdf 上传接口")
    except ContentExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("", response_model=CaptureRead, status_code=status.HTTP_202_ACCEPTED)
async def create_capture(
    payload: CaptureCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaptureRead:
    """提交文本/URL 内容，异步提取概念。"""
    raw_content = await _resolve_raw_content(payload)
    capture = await capture_service.create_capture(
        db, current_user.id, payload.domain, payload.source_type, raw_content, payload.source_url
    )
    background_tasks.add_task(capture_service.process_capture, capture.id)
    return CaptureRead.model_validate(capture)


@router.post("/pdf", response_model=CaptureRead, status_code=status.HTTP_202_ACCEPTED)
async def create_capture_pdf(
    background_tasks: BackgroundTasks,
    domain: Domain = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaptureRead:
    """上传 PDF 文件，异步提取概念。"""
    pdf_bytes = await file.read()
    try:
        raw_content = extract_from_pdf(pdf_bytes)
    except ContentExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    capture = await capture_service.create_capture(
        db, current_user.id, domain, CaptureSourceType.PDF, raw_content, None
    )
    background_tasks.add_task(capture_service.process_capture, capture.id)
    return CaptureRead.model_validate(capture)


@router.get("/{capture_id}", response_model=CaptureRead)
async def get_capture_status(
    capture_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaptureRead:
    capture = await capture_service.get_capture(db, capture_id, current_user.id)
    if capture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="捕获记录不存在")
    return CaptureRead.model_validate(capture)


@router.get("/{capture_id}/concepts", response_model=CaptureConceptsResponse)
async def get_capture_concepts(
    capture_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CaptureConceptsResponse:
    capture = await capture_service.get_capture(db, capture_id, current_user.id)
    if capture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="捕获记录不存在")

    nodes = await capture_service.get_capture_concepts(db, capture_id)
    concepts = [
        ConceptWithRelations(
            id=node.id,
            label=node.label,
            definition=node.definition,
            domain=node.domain,
            card_count=len(node.cards),
            related=[RelatedConceptRead(id=e.target_id, label="") for e in node.outgoing_edges],
        )
        for node in nodes
    ]
    return CaptureConceptsResponse(capture=CaptureRead.model_validate(capture), concepts=concepts)
