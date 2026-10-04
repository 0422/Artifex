import json
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StarRange, StarSort, StarSource
from app.models.star import Star
from app.schemas.star import (
    MAX_CONTENT_CHARS,
    PREVIEW_CHARS,
    StarCreate,
    StarImportRequest,
    StarUpdate,
    normalize_tags,
)

# 2026-10-03 新增摘星阁（M7）服务层：捕获 → 摘要 → 查询/筛选 → 随机抓取 → 导入。
#
# 关键决策：
#   1. 时区用固定 UTC+8（与 news_service.FIXED_TZ 同一约定）。Windows 无系统 tz
#      数据库，zoneinfo("Asia/Shanghai") 会因缺 tzdata 直接抛错（M6 踩过，见
#      docs/design/phases/M6.md 5-10）。
#   2. 标签筛选走 jsonb @> 而非关联表：个人标签量级几十个，GIN 索引足够，
#      省两张表 + 一个 join。
#   3. 标签统计在 Python 里数而不是 SQL unnest + group by：个人量级（千行以内）
#      全量拉 tags 数组比在 PG 里对集合返回函数分组更稳，也更好改。
#   4. 搜索用 ilike，%/\_ 已转义；个人量级远没到需要 pg_trgm 的程度。

FIXED_TZ = timezone(timedelta(hours=8))

# 「更早」与「本月」的分界：30 天。
MONTH_DAYS = 30
WEEK_DAYS = 7

SOURCE_LABELS: dict[StarSource, str] = {
    StarSource.MANUAL: "手写",
    StarSource.IMPORT: "导入",
    StarSource.NEWS: "世势洞察",
    StarSource.CHAT: "情境对话",
}

RANGE_LABELS: dict[StarRange, str] = {
    StarRange.ALL: "全部",
    StarRange.TODAY: "今天",
    StarRange.WEEK: "本周",
    StarRange.MONTH: "本月",
    StarRange.EARLIER: "更早",
}

# 首次进入的示例星：用户一颗都还没有时，空态给三条可直接抄的文案。
SAMPLE_STARS: tuple[str, ...] = (
    "原来「中庸」不是和稀泥，是「时中」——时机对了才叫中",
    "通勤路上想到：摘星阁这个名字本身就是一个好的产品隐喻",
    "TODO：把日语听力从「泛听」换成「精听 + 影子跟读」试两周",
)


def build_preview(content: str) -> str:
    """2026-10-03 生成星图摘要：折叠所有空白为单空格，截到 80 字，超出补省略号。

    折叠空白是必须的——备忘录里大量使用换行分段，而 preview 在星图的 tooltip
    与清单模式里都是单行渲染，不折叠会把 tooltip 撑成几行高。
    """
    flat = " ".join(content.split())
    if len(flat) <= PREVIEW_CHARS:
        return flat
    return flat[: PREVIEW_CHARS - 1].rstrip() + "…"


def _range_bounds(star_range: StarRange) -> tuple[datetime | None, datetime | None]:
    """返回 (起始, 截止)。任一为 None 表示该侧不设限。

    today 按固定 UTC+8 的自然日边界算，week/month 用滚动天数，earlier 是
    「早于 30 天」——沉底的老星，翻它们时的感觉像在阁楼的箱底摸旧纸条。
    """
    now = datetime.now(timezone.utc)
    if star_range is StarRange.ALL:
        return None, None
    if star_range is StarRange.TODAY:
        local_now = now.astimezone(FIXED_TZ)
        day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start.astimezone(timezone.utc), None
    if star_range is StarRange.WEEK:
        return now - timedelta(days=WEEK_DAYS), None
    if star_range is StarRange.MONTH:
        return now - timedelta(days=MONTH_DAYS), None
    cutoff = now - timedelta(days=MONTH_DAYS)
    return None, cutoff


def _escape_like(text: str) -> str:
    """ilike 的通配符转义：用户搜 100% 或 a_b 时，%/_ 必须按字面量匹配。"""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_stars(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    tag: str | None = None,
    star_range: StarRange = StarRange.ALL,
    sort: StarSort = StarSort.RECENT,
    favorite: bool = False,
    pinned: bool = False,
    archived: bool = False,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 200,
) -> tuple[list[Star], int]:
    """分页查询。默认排除已归档（is_archived=False），archived=True 时只看归档。

    置顶星在两种排序下都钉在最前：阁楼里用户自己插上去的那几颗，理应第一个被看到。
    """
    filters: list[Any] = [Star.user_id == user_id, Star.is_archived.is_(archived)]
    if tag:
        # jsonb @> '["标签"]'，走 tags 上的 GIN 索引
        filters.append(Star.tags.op("@>")(cast([tag], JSONB)))
    if favorite:
        filters.append(Star.is_favorite.is_(True))
    if pinned:
        filters.append(Star.is_pinned.is_(True))
    start, end = _range_bounds(star_range)
    if start is not None:
        filters.append(Star.created_at >= start)
    if end is not None:
        filters.append(Star.created_at < end)
    if keyword and keyword.strip():
        filters.append(Star.content.ilike(f"%{_escape_like(keyword.strip())}%", escape="\\"))

    # 最近回味的在前，从没被抓过的沉底（NULLS LAST，理由见 StarSort 定义）
    order = (
        [Star.is_pinned.desc(), Star.last_grabbed_at.desc().nulls_last(), Star.created_at.desc()]
        if sort is StarSort.REVISITED
        else [Star.is_pinned.desc(), Star.created_at.desc()]
    )

    total = await db.scalar(select(func.count()).select_from(Star).where(*filters)) or 0
    result = await db.execute(
        select(Star).where(*filters).order_by(*order).limit(page_size).offset((page - 1) * page_size)
    )
    return list(result.scalars().all()), total


async def get_star(db: AsyncSession, star_id: uuid.UUID, user_id: uuid.UUID) -> Star | None:
    """按 id 取详情。带 user_id 条件而不是只按 id：别人夜空里的星，这里应当 404
    而不是 403——不泄漏"这个 id 存在"这件事。"""
    result = await db.execute(
        select(Star).where(Star.id == star_id, Star.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def random_stars(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    count: int = 3,
    tag: str | None = None,
) -> list[Star]:
    """「伸手抓一把」：从未归档的星里随机取 count 颗全文。

    用 order by random() 而不是先取全部再 Python 采样：个人量级（千行）下
    PG 顺序扫描足够，且不必为采样把全表读进内存。
    """
    filters: list[Any] = [Star.user_id == user_id, Star.is_archived.is_(False)]
    if tag:
        filters.append(Star.tags.op("@>")(cast([tag], JSONB)))
    result = await db.execute(
        select(Star).where(*filters).order_by(func.random()).limit(count)
    )
    return list(result.scalars().all())


async def list_tags(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[str, int]]:
    """标签 + 使用计数，按计数降序。在 Python 里数（见文件头决策 3）。"""
    result = await db.execute(
        select(Star.tags).where(Star.user_id == user_id, Star.is_archived.is_(False))
    )
    counter: Counter[str] = Counter()
    for (tags,) in result.all():
        if tags:
            counter.update(tags)
    return counter.most_common()


def _apply(star: Star, payload: StarUpdate) -> None:
    """把局部更新铺到 ORM 实例上。content 变了才重算 preview——标签/置顶的修改
    不该动摘要，否则星图上的文案会因为一次收藏而变短。"""
    data = payload.model_dump(exclude_unset=True)
    if "content" in data and data["content"] is not None:
        star.content = data["content"]
        star.preview = build_preview(data["content"])
    if "tags" in data and data["tags"] is not None:
        star.tags = normalize_tags(data["tags"])
    for key in ("is_pinned", "is_favorite", "is_archived"):
        if key in data and data[key] is not None:
            setattr(star, key, data[key])


async def create_star(
    db: AsyncSession, user_id: uuid.UUID, payload: StarCreate
) -> Star:
    # 新建走显式赋值而不复用 _apply：_apply 用的是 exclude_unset=True，
    # 客户端没传 tags/is_pinned 时这些键不在 data 里，实例上会留下 None 而不是默认值。
    # is_archived 也显式给 False：SQLAlchemy 的列默认值要等 flush 才生效，
    # 在此之前实例属性是 None，序列化或测试断言都会踩空。
    star = Star(
        user_id=user_id,
        source=payload.source,
        origin_ref=payload.origin_ref,
        content=payload.content,
        preview=build_preview(payload.content),
        tags=normalize_tags(payload.tags),
        is_pinned=payload.is_pinned,
        is_favorite=payload.is_favorite,
        is_archived=False,
    )
    db.add(star)
    await db.commit()
    await db.refresh(star)
    return star


async def update_star(db: AsyncSession, star: Star, payload: StarUpdate) -> Star:
    _apply(star, payload)
    await db.commit()
    await db.refresh(star)
    return star


async def delete_star(db: AsyncSession, star: Star) -> None:
    await db.delete(star)
    await db.commit()


async def mark_grabbed(db: AsyncSession, star: Star) -> None:
    """记录一次"抓取"（打开详情）。

    这是一个刻意做在 GET 上的写副作用：单用户量级下每次读多一条 UPDATE 可忽略，
    而「抓」是这个模块的核心动词，留下 last_grabbed_at 才能支撑将来的
    「最常回味的星」排序。代价是 GET 不再纯净——若将来要上缓存，这一行要一起挪走。
    """
    star.last_grabbed_at = datetime.now(timezone.utc)
    await db.commit()
    # 必须 refresh：commit 后实例上的属性已过期，而 expire_on_commit=False
    # 时不会自动重新加载，不 refresh 的话同一响应里的 updated_at 是旧值，
    # 抽屉的"改于"永远慢一拍
    await db.refresh(star)


async def export_stars(db: AsyncSession, user_id: uuid.UUID, fmt: str = "md") -> tuple[str, str]:
    """把整片夜空导出成一个文件。返回 (文件名, 文本内容)。

    为什么必须有：星星是最私人的数据，全站又没有别的导出入口。
    「随时能整个带走」是信任功能，不是锦上添花——用户不敢把念头
    长期存在一个搬不走的地方。

    不走分页直接全量：个人量级（千行以内）一次读完，导出本来就是
    要全量的动作，分页只会把问题搞复杂。
    """
    result = await db.execute(
        select(Star)
        .where(Star.user_id == user_id)
        .order_by(Star.is_pinned.desc(), Star.created_at.desc())
    )
    stars = list(result.scalars().all())
    stamp = datetime.now(FIXED_TZ).strftime("%Y%m%d")
    if fmt == "json":
        payload = [
            {
                "content": star.content,
                "tags": star.tags,
                "is_pinned": star.is_pinned,
                "is_favorite": star.is_favorite,
                "is_archived": star.is_archived,
                "source": star.source.value,
                "origin_ref": str(star.origin_ref) if star.origin_ref else None,
                "created_at": star.created_at.isoformat(),
                "updated_at": star.updated_at.isoformat(),
                "last_grabbed_at": star.last_grabbed_at.isoformat() if star.last_grabbed_at else None,
            }
            for star in stars
        ]
        # ensure_ascii=False：导出是给人读的，中文不该变成 \uXXXX
        return f"artifex-stars-{stamp}.json", json.dumps(payload, ensure_ascii=False, indent=2)

    lines = [
        "# Artifex · 摘星阁",
        "",
        f"共 {len(stars)} 颗星，导出于 {datetime.now(FIXED_TZ).strftime('%Y-%m-%d %H:%M')}（UTC+8）",
        "",
    ]
    for star in stars:
        local = star.created_at.astimezone(FIXED_TZ)
        badges = []
        if star.is_pinned:
            badges.append("📌")
        if star.is_favorite:
            badges.append("★")
        if star.is_archived:
            badges.append("已归档")
        badge_text = f" {' '.join(badges)}" if badges else ""
        lines.append(f"## {local.strftime('%Y-%m-%d %H:%M')}{badge_text}")
        if star.tags:
            lines.append("")
            lines.append("标签：" + "、".join(f"#{name}" for name in star.tags))
        lines.append("")
        lines.append(star.content)
        lines.append("")
    return f"artifex-stars-{stamp}.md", "\n".join(lines)


async def import_stars(
    db: AsyncSession, user_id: uuid.UUID, payload: StarImportRequest
) -> tuple[int, int]:
    """批量导入，一行一颗。返回 (新建数, 跳过数)。

    跳过四种行：纯空白行（粘贴时常带）、批次内重复、与夜空中已有内容完全相同、
    超过单颗正文字符上限的。最后一种用 skip 而不是 422 拒绝整批——一次粘贴
    两百行里混进一条超长的，为它废掉整次导入太不值。
    """
    created = 0
    skipped = 0
    seen: set[str] = set()
    shared_tags = normalize_tags(payload.tags)
    stars: list[Star] = []
    candidates: list[str] = []
    for raw in payload.lines:
        content = raw.strip()
        if not content or content in seen or len(content) > MAX_CONTENT_CHARS:
            skipped += 1
            continue
        seen.add(content)
        candidates.append(content)

    # 与已有内容比对：用户重复粘贴同一段旧笔记时，不该凭空多出一把一模一样的星。
    # content 上没有索引，走 ix_stars_user_id 再过滤；个人量级（千行）无所谓。
    if candidates:
        existing = await db.execute(
            select(Star.content).where(Star.user_id == user_id, Star.content.in_(candidates))
        )
        duplicates = {row[0] for row in existing.all()}
    else:
        duplicates = set()

    for content in candidates:
        if content in duplicates:
            skipped += 1
            continue
        # tags 每颗拷贝一份：JSONB 列每次 flush 各自序列化，共用同一个 list
        # 对象在将来若改成原地修改会有 aliasing 风险，拷贝是最省心的做法
        stars.append(
            Star(
                user_id=user_id,
                source=StarSource.IMPORT,
                content=content,
                preview=build_preview(content),
                tags=list(shared_tags),
            )
        )
    if stars:
        db.add_all(stars)
        await db.commit()
        created = len(stars)
    return created, skipped
