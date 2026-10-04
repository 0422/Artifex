import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import quote

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import StarRange, StarSort
from app.models.star import Star
from app.models.user import User
from app.schemas.star import (
    StarCreate,
    StarImportRequest,
    StarImportResult,
    StarPage,
    StarRandomRequest,
    StarRead,
    StarTagCount,
    StarUpdate,
)
from app.services import star_service

# 2026-10-03 新增摘星阁（M7）模块 API：捕获 / 查询 / 抓取详情 / 随机抓一把 / 标签 / 导入。
# 全部端点都按当前登录用户过滤，星星是最私人的数据，不做任何全局共享。
router = APIRouter(prefix="/stars", tags=["stars"])


async def _load_owned_star(
    db: AsyncSession, star_id: uuid.UUID, user_id: uuid.UUID, *, mark: bool = False
) -> Star:
    """按 id + user_id 取星，不存在就 404（不区分"不存在"与"不是你的"）。"""
    star = await star_service.get_star(db, star_id, user_id)
    if star is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="这颗星不存在或已坠落")
    if mark:
        await star_service.mark_grabbed(db, star)
    return star


@router.get("", response_model=StarPage)
async def list_stars(
    tag: str | None = None,
    star_range: StarRange = Query(default=StarRange.ALL, alias="range"),
    sort: StarSort = Query(default=StarSort.RECENT),
    favorite: bool = False,
    pinned: bool = False,
    archived: bool = False,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    # 上限 200：星图一次渲染 200 颗是 DOM 方案的舒适区，再多要换成 Canvas
    # （见 docs/design/phases/M7.md 9-2）。超出部分靠"加载更多"追加。
    page_size: int = Query(default=200, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StarPage:
    items, total = await star_service.list_stars(
        db,
        current_user.id,
        tag=tag,
        star_range=star_range,
        sort=sort,
        favorite=favorite,
        pinned=pinned,
        archived=archived,
        keyword=q,
        page=page,
        page_size=page_size,
    )
    return StarPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/tags", response_model=list[StarTagCount])
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StarTagCount]:
    pairs = await star_service.list_tags(db, current_user.id)
    return [StarTagCount(name=name, count=count) for name, count in pairs]


@router.get("/export")
async def export_stars(
    fmt: Literal["md", "json"] = "md",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """把整片夜空打包下载。手写的 Response 而不走 response_model：要带
    Content-Disposition 让浏览器存成文件，并且中文文件名需要 RFC 5987 编码
    （否则 Windows 上下载下来是乱码名）。"""
    filename, text = await star_service.export_stars(db, current_user.id, fmt)
    media_type = "application/json" if fmt == "json" else "text/markdown"
    # ascii 兜底名 + filename* 双写：老浏览器只看前者，新浏览器用后者拿中文名
    quoted = quote(filename)
    return Response(
        content=text,
        media_type=f"{media_type}; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"stars.{fmt}\"; filename*=UTF-8''{quoted}"
            )
        },
    )


@router.post("/random", response_model=list[StarRead])
async def random_stars(
    payload: StarRandomRequest,
    tag: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StarRead]:
    """「伸手抓一把」：随机取 N 颗全文。抽屉里直接可读，不需要再逐颗请求详情。"""
    stars = await star_service.random_stars(
        db, current_user.id, count=payload.count, tag=tag
    )
    return [StarRead.model_validate(star) for star in stars]


@router.post("/import", response_model=StarImportResult)
async def import_stars(
    payload: StarImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StarImportResult:
    """批量导入：一行一颗星。用户从别处搬旧备忘录进来的主要入口。"""
    created, skipped = await star_service.import_stars(db, current_user.id, payload)
    return StarImportResult(created=created, skipped=skipped)


@router.get("/{star_id}", response_model=StarRead)
async def get_star(
    star_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StarRead:
    star = await _load_owned_star(db, star_id, current_user.id, mark=True)
    return StarRead.model_validate(star)


@router.post("", response_model=StarRead, status_code=status.HTTP_201_CREATED)
async def create_star(
    payload: StarCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StarRead:
    star = await star_service.create_star(db, current_user.id, payload)
    return StarRead.model_validate(star)


@router.patch("/{star_id}", response_model=StarRead)
async def update_star(
    star_id: uuid.UUID,
    payload: StarUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StarRead:
    star = await _load_owned_star(db, star_id, current_user.id)
    star = await star_service.update_star(db, star, payload)
    return StarRead.model_validate(star)


@router.delete("/{star_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_star(
    star_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    star = await _load_owned_star(db, star_id, current_user.id)
    await star_service.delete_star(db, star)
