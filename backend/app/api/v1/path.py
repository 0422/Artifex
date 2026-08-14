from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.path import LearningPathRead, OnboardingCompleteRequest, OnboardingQuestion
from app.services import path_service

router = APIRouter(prefix="/path", tags=["path"])


@router.get("/onboarding", response_model=list[OnboardingQuestion])
async def get_onboarding(current_user: User = Depends(get_current_user)) -> list[OnboardingQuestion]:
    """获取 5 分钟引导的问题列表。"""
    return path_service.get_onboarding_questions()


@router.post("/onboarding/complete", response_model=LearningPathRead, status_code=status.HTTP_201_CREATED)
async def complete_onboarding(
    payload: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LearningPathRead:
    """完成引导，生成起点报告 + 初始学习路径。"""
    path = await path_service.complete_onboarding(db, current_user.id, payload.domain, payload.answers)
    return LearningPathRead.model_validate(path)


@router.get("/current", response_model=LearningPathRead)
async def get_current_path(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LearningPathRead:
    """获取用户当前的学习路径。"""
    path = await path_service.get_current_path(db, current_user.id)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未生成学习路径，请先完成引导")
    return LearningPathRead.model_validate(path)
