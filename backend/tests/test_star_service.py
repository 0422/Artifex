import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import StarRange, StarSource
from app.models.star import Star
from app.schemas.star import (
    MAX_CONTENT_CHARS,
    MAX_TAGS_PER_STAR,
    PREVIEW_CHARS,
    StarCreate,
    StarImportRequest,
    StarUpdate,
    normalize_tags,
)
from app.services import star_service

# 2026-10-03 摘星阁（M7）服务层测试，仿 test_news_service.py 的 mock 手法。
# 这里只覆盖【不需要真库】的部分：preview/标签/时间边界是纯函数，create/import
# 用 MagicMock(spec=AsyncSession) 断言落库形态。SQL 两端（list_stars / random_stars）
# 依赖真实 PG 的 jsonb @> 与 func.random()，留给集成环境验证。


@pytest.fixture
def db() -> MagicMock:
    """带 execute 的 AsyncSession mock。

    必须显式配置 execute：MagicMock(spec=AsyncSession) 虽把 execute 造成 AsyncMock，
    但它的 return_value 的 .all() 同样是协程；而生产路径上 await db.execute(...)
    拿到的是 ChunkedIteratorResult，其 .all() 与 .scalars().all() 都是【同步】的。
    mock 形态与真实形态不一致，会让 import_stars 里的
    {row[0] for row in existing.all()} 报 TypeError: 'coroutine' object is not
    iterable——那是假失败，不是代码缺陷（实测确认过 ChunkedIteratorResult.all()
    同步，见 tests 目录下本次排查记录）。
    """
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    return session


def db_with_existing(rows: list[tuple]) -> MagicMock:
    """让 execute 的 .all() 返回指定行，用于模拟"夜空中已有这些内容"。"""
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


# ---------- preview ----------


def test_build_preview_collapses_newlines():
    content = "第一行\n\n第二行\t\t制表\r\n第三行"
    assert star_service.build_preview(content) == "第一行 第二行 制表 第三行"


def test_build_preview_truncates_with_ellipsis():
    content = "甲" * 200
    preview = star_service.build_preview(content)
    assert len(preview) == PREVIEW_CHARS
    assert preview.endswith("…")
    # 截断按字符而非字节：中文不会出现半字
    assert "�" not in preview


def test_build_preview_keeps_short_content_verbatim():
    assert star_service.build_preview("  短念头  ") == "短念头"


def test_build_preview_truncation_does_not_trail_space():
    # 第 79 个字符恰好是空格时，省略号不应孤零零挂在空格后
    preview = star_service.build_preview("甲" * 79 + " " + "乙" * 100)
    assert preview.endswith("…")
    assert not preview.endswith(" …")


# ---------- 标签 ----------


def test_normalize_tags_dedupes_and_strips():
    assert normalize_tags([" 灵感 ", "灵感", "英语", ""]) == ["灵感", "英语"]


def test_normalize_tags_caps_count_and_length():
    tags = [f"标签{i}" for i in range(50)]
    assert len(normalize_tags(tags)) == MAX_TAGS_PER_STAR
    assert normalize_tags(["x" * 100]) == ["x" * 30]


# ---------- 时间边界 ----------


def test_range_bounds_all_has_no_bound():
    assert star_service._range_bounds(StarRange.ALL) == (None, None)


def test_range_bounds_today_is_local_midnight():
    start, end = star_service._range_bounds(StarRange.TODAY)
    assert start is not None and end is None
    local = start.astimezone(star_service.FIXED_TZ)
    assert (local.hour, local.minute, local.second) == (0, 0, 0)
    # 起点不可能落在未来
    assert start <= datetime.now(timezone.utc)


def test_range_bounds_earlier_is_upper_bound_only():
    start, end = star_service._range_bounds(StarRange.EARLIER)
    assert start is None
    assert end is not None and end < datetime.now(timezone.utc) - timedelta(days=29)


# ---------- 通配符转义 ----------


def test_escape_like_escapes_wildcards():
    assert star_service._escape_like("100%") == "100\\%"
    assert star_service._escape_like("a_b") == "a\\_b"


# ---------- 落库 ----------


@pytest.mark.asyncio
async def test_create_star_computes_preview_and_defaults(db: MagicMock):
    star = await star_service.create_star(
        db, uuid.uuid4(), StarCreate(content="\n  多行\n念头  ", tags=["灵感", "灵感"])
    )
    assert star.preview == "多行 念头"
    # 重复标签只留一个，且顺序取首次出现
    assert star.tags == ["灵感"]
    # 客户端没传的开关不应该是 None——SQLAlchemy 的列默认值要等 flush 才生效，
    # 这里断言的是"实例一造出来就是完整的"，不然序列化会在 flush 前踩空
    assert star.is_pinned is False
    assert star.is_favorite is False
    assert star.is_archived is False
    assert star.source is StarSource.MANUAL
    db.add.assert_called_once_with(star)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_star_recomputes_preview_only_when_content_changes(db: MagicMock):
    star = Star(id=uuid.uuid4(), user_id=uuid.uuid4(), content="旧内容", preview="旧内容")
    await star_service.update_star(db, star, StarUpdate(is_favorite=True))
    assert star.preview == "旧内容"
    assert star.is_favorite is True

    await star_service.update_star(db, star, StarUpdate(content="换了个新念头"))
    assert star.preview == "换了个新念头"


@pytest.mark.asyncio
async def test_import_stars_skips_blank_and_duplicate_lines(db: MagicMock):
    created, skipped = await star_service.import_stars(
        db,
        uuid.uuid4(),
        StarImportRequest(lines=["第一颗", "  ", "第二颗", "第一颗", "\t"]),
    )
    assert (created, skipped) == (2, 3)
    assert db.add_all.call_count == 1
    assert len(db.add_all.call_args[0][0]) == 2


@pytest.mark.asyncio
async def test_import_stars_with_only_blanks_writes_nothing(db: MagicMock):
    created, skipped = await star_service.import_stars(
        db, uuid.uuid4(), StarImportRequest(lines=["  ", "\n"])
    )
    assert (created, skipped) == (0, 2)
    db.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_import_stars_applies_shared_tags(db: MagicMock):
    created, _ = await star_service.import_stars(
        db, uuid.uuid4(), StarImportRequest(lines=["甲", "乙"], tags=["旧备忘录", "旧备忘录"])
    )
    assert created == 2
    for star in db.add_all.call_args[0][0]:
        assert star.tags == ["旧备忘录"]


@pytest.mark.asyncio
async def test_import_stars_skips_overlong_lines(db: MagicMock):
    # 超长行不该让整批导入 422，而是跳过并计入 skipped
    created, skipped = await star_service.import_stars(
        db,
        uuid.uuid4(),
        StarImportRequest(lines=["正常的一颗", "超" * (MAX_CONTENT_CHARS + 1)]),
    )
    assert (created, skipped) == (1, 1)


@pytest.mark.asyncio
async def test_import_stars_skips_lines_already_in_the_sky(db: MagicMock):
    # 与夜空中已有内容完全相同的行要跳过，否则重复粘贴会凭空多出一把一样的星
    existing_db = db_with_existing([("甲",)])
    created, skipped = await star_service.import_stars(
        existing_db, uuid.uuid4(), StarImportRequest(lines=["甲", "乙"])
    )
    assert (created, skipped) == (1, 1)


@pytest.mark.asyncio
async def test_imported_stars_mark_source_as_import(db: MagicMock):
    await star_service.import_stars(db, uuid.uuid4(), StarImportRequest(lines=["从别处搬来的"]))
    assert db.add_all.call_args[0][0][0].source is StarSource.IMPORT


# ---------- 跨模块转存与导出（2026-10-03，M7 第 7 节 #2 / #5）----------


@pytest.mark.asyncio
async def test_create_star_passes_through_source_and_origin(db: MagicMock):
    """跨模块转存（世势洞察 -> 星）由调用方带 source/origin_ref，服务层必须原样落库。"""
    origin = uuid.uuid4()
    star = await star_service.create_star(
        db,
        uuid.uuid4(),
        StarCreate(content="一条想留下的新闻", source=StarSource.NEWS, origin_ref=origin),
    )
    assert star.source is StarSource.NEWS
    assert star.origin_ref == origin


def _star_row(**kwargs) -> Star:
    created = datetime(2026, 10, 1, 14, 30, tzinfo=timezone.utc)
    base = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        preview=kwargs.get("content", ""),
        created_at=created,
        updated_at=created,
    )
    base.update(kwargs)
    return Star(**base)


def _db_returning(rows: list[Star]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_export_markdown_marks_badges_and_uses_fixed_tz():
    rows = [
        _star_row(content="被钉住的一条", tags=["灵感"], is_pinned=True, is_favorite=True),
        _star_row(content="归档掉的一条", is_archived=True),
    ]
    filename, text = await star_service.export_stars(_db_returning(rows), rows[0].user_id, "md")
    assert filename.startswith("artifex-stars-")
    assert filename.endswith(".md")
    # 置顶/收藏/归档三种状态都要在标题行露出标记，否则导出的文件读不出主次
    assert "📌 ★" in text
    assert "已归档" in text
    assert "标签：#灵感" in text
    assert "被钉住的一条" in text
    # 时间按固定 UTC+8 折算：14:30 UTC -> 22:30
    assert "## 2026-10-01 22:30" in text


@pytest.mark.asyncio
async def test_export_json_keeps_chinese_and_full_metadata():
    rows = [_star_row(content="中文不该变成转义", tags=["灵感"], source=StarSource.NEWS)]
    filename, text = await star_service.export_stars(_db_returning(rows), rows[0].user_id, "json")
    assert filename.endswith(".json")
    payload = json.loads(text)
    assert payload[0]["content"] == "中文不该变成转义"
    assert payload[0]["tags"] == ["灵感"]
    assert payload[0]["source"] == "news"


@pytest.mark.asyncio
async def test_export_with_no_stars_still_returns_a_file():
    filename, text = await star_service.export_stars(_db_returning([]), uuid.uuid4(), "md")
    assert filename.endswith(".md")
    assert "共 0 颗星" in text


# ---------- 需真库的两端（占位，集成环境补） ----------
# list_stars：jsonb @> 筛选 + 复合索引 + 分页边界
# random_stars：order by random() + 归档排除
# list_tags：Python 侧 Counter 聚合
# get_star：user_id 隔离（别人的星必须取不到）
