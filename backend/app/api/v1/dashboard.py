import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardOverview,
    DashboardSessionDetail,
    DashboardSessionPage,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOverview:
    return await dashboard_service.get_overview(db, current_user.id)


@router.get("/sessions", response_model=DashboardSessionPage)
async def get_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSessionPage:
    return await dashboard_service.get_sessions(db, current_user.id, page, page_size)


@router.get("/sessions/{session_id}", response_model=DashboardSessionDetail)
async def get_session_detail(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSessionDetail:
    detail = await dashboard_service.get_session_detail(db, current_user.id, session_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="对话记录不存在"
        )
    return detail
