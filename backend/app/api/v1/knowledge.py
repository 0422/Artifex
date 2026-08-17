import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeCategoryCreate,
    KnowledgeCategoryRead,
    KnowledgeCategoryTree,
    KnowledgeCategoryUpdate,
)
from app.services import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/categories/tree", response_model=list[KnowledgeCategoryTree])
async def get_category_tree(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeCategoryTree]:
    categories = await knowledge_service.list_categories(db, current_user.id)
    return [
        KnowledgeCategoryTree.model_validate(node)
        for node in knowledge_service.build_category_tree(categories)
    ]


@router.post(
    "/categories",
    response_model=KnowledgeCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: KnowledgeCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeCategoryRead:
    try:
        category = await knowledge_service.create_category(db, current_user.id, payload)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error
    return KnowledgeCategoryRead.model_validate(category)


@router.put("/categories/{category_id}", response_model=KnowledgeCategoryRead)
async def update_category(
    category_id: uuid.UUID,
    payload: KnowledgeCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeCategoryRead:
    category = await knowledge_service.get_category(db, category_id, current_user.id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    try:
        category = await knowledge_service.update_category(db, category, payload)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
        ) from error
    return KnowledgeCategoryRead.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    category = await knowledge_service.get_category(db, category_id, current_user.id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    await knowledge_service.archive_category(db, category)
