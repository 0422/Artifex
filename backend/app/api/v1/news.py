import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.enums import NewsDomain
from app.models.news import NewsDigest, NewsSource
from app.models.user import User
from app.schemas.news import (
    NewsArticlePage,
    NewsDigestGenerateRequest,
    NewsDigestPage,
    NewsDigestRead,
    NewsFetchResult,
    NewsSourceCreate,
    NewsSourceRead,
    NewsSourceUpdate,
)
from app.services import news_service

# 2026-10-03 新增世势洞察（M6）模块 API：来源 CRUD、手动抓取、日报查询/生成、原始文章流。
router = APIRouter(prefix="/news", tags=["news"])


# ---------- 来源管理 ----------


@router.get("/sources", response_model=list[NewsSourceRead])
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NewsSourceRead]:
    sources = await news_service.list_sources(db)
    return [NewsSourceRead.model_validate(source) for source in sources]


@router.post(
    "/sources", response_model=NewsSourceRead, status_code=status.HTTP_201_CREATED
)
async def create_source(
    payload: NewsSourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsSourceRead:
    source = await news_service.create_source(db, payload)
    return NewsSourceRead.model_validate(source)


@router.patch("/sources/{source_id}", response_model=NewsSourceRead)
async def update_source(
    source_id: uuid.UUID,
    payload: NewsSourceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsSourceRead:
    source = await news_service.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="新闻源不存在")
    source = await news_service.update_source(db, source, payload)
    return NewsSourceRead.model_validate(source)


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    source = await news_service.get_source(db, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="新闻源不存在")
    await news_service.delete_source(db, source)


# ---------- 抓取与日报 ----------


@router.post("/fetch", response_model=NewsFetchResult)
async def fetch_news(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsFetchResult:
    """手动触发一轮全量抓取。同步执行并整体限时，前端按钮点击后 toast 反馈结果。"""
    settings = get_settings()
    # fetch_all_sources 内部按源并发、单源有超时；这里再给一个整体上限，
    # 防止源很多时按钮长时间转圈
    budget = min(90.0, settings.news_fetch_timeout_seconds * 3 + 10)
    try:
        result = await asyncio.wait_for(
            news_service.fetch_all_sources(db), timeout=budget
        )
    except TimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="抓取超时，请稍后重试或减少启用源",
        ) from error
    return NewsFetchResult(**result)


@router.get("/digests", response_model=NewsDigestPage)
async def list_digests(
    domain: NewsDomain | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsDigestPage:
    items, total = await news_service.list_digests(db, domain, page, page_size)
    return NewsDigestPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/digests/{digest_id}", response_model=NewsDigestRead)
async def get_digest(
    digest_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsDigestRead:
    digest = await news_service.get_digest(db, digest_id)
    if digest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日报不存在")
    return NewsDigestRead.model_validate(digest)


@router.post("/digests/generate", response_model=list[NewsDigestRead])
async def generate_digests(
    payload: NewsDigestGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NewsDigestRead]:
    """手动生成日报：带 domain 只生成该板块，否则六个板块各一份（并发）。
    返回可能为空列表（窗口内所有板块都没文章）。"""
    if payload.domain is not None:
        digest = await news_service.generate_digest(db, payload.domain, payload.digest_date)
        digests = [digest] if digest is not None else []
    else:
        digests = await news_service.generate_all_digests(payload.digest_date)
    return [NewsDigestRead.model_validate(digest) for digest in digests]


@router.get("/articles", response_model=NewsArticlePage)
async def list_articles(
    domain: NewsDomain | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsArticlePage:
    items, total = await news_service.list_articles(db, domain, page, page_size)
    return NewsArticlePage(items=items, total=total, page=page, page_size=page_size)
