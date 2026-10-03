import asyncio
import hashlib
import html
import logging
import re
from datetime import datetime, time, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx
from openai import OpenAIError
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import llm
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.enums import NewsDomain
from app.models.news import NewsArticle, NewsDigest, NewsSource
from app.schemas.news import NewsDigestContent, NewsDigestItem, NewsSourceCreate, NewsSourceUpdate

logger = logging.getLogger(__name__)

# 2026-10-03 新增世势洞察（M6）服务层：抓取 → 去重入库 → LLM 按板块生成日报 → 查询。
# 关键决策：
#   1. 时区用固定 UTC+8 而非 zoneinfo("Asia/Shanghai")——Windows 无系统 tz 数据库，
#      zoneinfo 会因缺 tzdata 包直接抛错；部署机在中国，固定偏移量足够。
#   2. fetch_all_sources 给每个源开独立子 session 并发抓取：AsyncSession 不是
#      协程安全的，共用同一 session gather 会交叉污染事务。
#   3. LLM 失败不抛异常，走 _degraded_content 降级稿（仿 report_service），
#      页面能看到原始标题列表而不是空白。

FIXED_TZ = timezone(timedelta(hours=8))

DOMAIN_LABELS: dict[NewsDomain, str] = {
    NewsDomain.AI: "AI",
    NewsDomain.TECH: "科技",
    NewsDomain.FINANCE: "财经",
    NewsDomain.EDUCATION: "教育",
    NewsDomain.WORLD: "国际",
    NewsDomain.GENERAL: "综合",
}

# 部分站点（如 The Verge）对默认 python-httpx UA 直接 403，带一个常见浏览器 UA
FETCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 ArtifexNewsBot/1.0"
)
# 单源单次最多处理多少条 entry，防个别 feed 一次吐几千条拖垮循环
MAX_ENTRIES_PER_SOURCE = 100
# 单份日报策展条数上限，同步写进 LLM payload 的 max_items
MAX_DIGEST_ITEMS = 8
EXCERPT_MAX_CHARS = 300

_TAG_RE = re.compile(r"<[^>]+>")
_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAMS = {"ref", "ref_src", "from", "spm", "fbclid", "gclid"}


def _short_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}".strip()
    return text[:200]


def _normalize_url(url: str) -> str:
    """去掉 utm_* / fbclid 一类跟踪参数并小写 scheme+host，让同一篇文章的
    不同渠道链接算出同一个指纹。"""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith(_TRACKING_PARAM_PREFIXES) and key.lower() not in _TRACKING_PARAMS
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), "")
    )


def _fingerprint(url: str) -> str:
    return hashlib.sha1(_normalize_url(url).encode("utf-8")).hexdigest()


def _strip_html(text: str) -> str:
    """feed 的 description 常带 HTML 标签与实体，摘要只留纯文本。"""
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", text))).strip()


def _entry_datetime(entry: dict) -> datetime | None:
    """feedparser 的 *_parsed 是 UTC struct_time；取不到返回 None，
    下游用 coalesce(published_at, created_at) 兜底。"""
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)
    return None


async def fetch_source(db: AsyncSession, source: NewsSource) -> int:
    """抓取单个源并入库新文章，返回新增条数。

    抓取或解析失败只把原因写进 source.last_error 后正常返回，不抛异常——
    整批抓取里单个源失效不应该让其余源也失败。
    """
    settings = get_settings()
    headers = {"User-Agent": FETCH_USER_AGENT, "Accept": "application/atom+xml, application/rss+xml, text/xml, */*"}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.news_fetch_timeout_seconds),
            follow_redirects=True,
        ) as client:
            response = await client.get(source.url, headers=headers)
            response.raise_for_status()
        payload = response.content
    except httpx.HTTPError as exc:
        source.last_error = _short_error(exc)
        await db.commit()
        logger.info("新闻源抓取失败 %s（%s）：%s", source.name, source.url, exc)
        return 0

    parsed = feedparser.parse(payload)
    entries = list(parsed.entries)[:MAX_ENTRIES_PER_SOURCE]
    if not entries:
        source.last_error = "feed 无可解析条目（源可能已失效或不是 RSS/Atom）"
        await db.commit()
        logger.info("新闻源无条目 %s（%s），bozo=%s", source.name, source.url, bool(parsed.bozo))
        return 0

    rows: list[NewsArticle] = []
    fingerprints: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        url = (entry.get("link") or "").strip()
        title = _strip_html(entry.get("title") or "").strip()
        if not url or not title:
            continue
        fingerprint = _fingerprint(url)
        # 同一 feed 内也可能重复给同一链接，批次内先去重一次
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        fingerprints.append(fingerprint)
        rows.append(
            NewsArticle(
                source_id=source.id,
                domain=source.domain,
                title=title[:300],
                url=url[:500],
                fingerprint=fingerprint,
                excerpt=_strip_html(entry.get("summary") or entry.get("description") or "")[:EXCERPT_MAX_CHARS] or None,
                published_at=_entry_datetime(entry),
            )
        )

    existing: set[str] = set()
    if fingerprints:
        result = await db.execute(
            select(NewsArticle.fingerprint).where(NewsArticle.fingerprint.in_(fingerprints))
        )
        existing = set(result.scalars().all())
    new_rows = [row for row in rows if row.fingerprint not in existing]
    if new_rows:
        db.add_all(new_rows)

    source.last_fetched_at = datetime.now(timezone.utc)
    source.last_error = None
    await db.commit()
    logger.info(
        "新闻源抓取完成 %s：候选 %d，新入库 %d", source.name, len(rows), len(new_rows)
    )
    return len(new_rows)


async def fetch_all_sources(db: AsyncSession) -> dict:
    """并发抓取所有启用源。每个源在独立子 session 里跑，互不干扰。"""
    settings = get_settings()
    result = await db.execute(
        select(NewsSource).where(NewsSource.is_enabled.is_(True)).order_by(NewsSource.created_at)
    )
    sources = list(result.scalars().all())
    if not sources:
        return {"total_sources": 0, "succeeded": 0, "failed": 0, "new_articles": 0}

    # 比单源超时多留 5 秒余量：fetch_source 内部的 httpx 超时先触发，
    # 外层 wait_for 只是防解析阶段卡死的兜底
    per_source_budget = settings.news_fetch_timeout_seconds + 5

    async def run_one(source_id) -> dict:
        async with async_session_factory() as session:
            source = await session.get(NewsSource, source_id)
            if source is None:
                return {"ok": False, "new": 0}
            try:
                count = await asyncio.wait_for(
                    fetch_source(session, source), timeout=per_source_budget
                )
                return {"ok": True, "new": count}
            except Exception as exc:  # fetch_source 只拦 httpx，这里防解析期意外
                source.last_error = _short_error(exc)
                await session.commit()
                logger.warning("新闻源抓取异常 %s：%s", source.name, exc)
                return {"ok": False, "new": 0}

    outcomes = await asyncio.gather(*(run_one(source.id) for source in sources))
    succeeded = sum(1 for outcome in outcomes if outcome["ok"])
    return {
        "total_sources": len(sources),
        "succeeded": succeeded,
        "failed": len(sources) - succeeded,
        "new_articles": sum(outcome["new"] for outcome in outcomes),
    }


def _window_bounds(digest_date, window_hours: int) -> tuple[datetime, datetime]:
    """日报取材窗口：[板块日当天 0 点 - window_hours, 板块日次日 0 点 与现在 的较小值]。

    往前多取 36 小时是为了让昨晚发布的稿件进次日早报；end 取 min(次日0点, now)
    避免把未来的抓取结果算进来（手动补生成历史日期时尤为关键）。
    """
    day_start = datetime.combine(digest_date, time.min, tzinfo=FIXED_TZ)
    end = min(day_start + timedelta(days=1), datetime.now(timezone.utc) + timedelta(minutes=1))
    return day_start - timedelta(hours=window_hours), end


async def _load_articles_for_digest(
    db: AsyncSession,
    domain: NewsDomain,
    digest_date,
    window_hours: int,
    limit: int,
) -> list[NewsArticle]:
    start, end = _window_bounds(digest_date, window_hours)
    recency = func.coalesce(NewsArticle.published_at, NewsArticle.created_at)
    result = await db.execute(
        select(NewsArticle)
        .where(NewsArticle.domain == domain, recency >= start, recency <= end)
        # source 关系异步下必须显式加载，否则拼 payload 时触发 lazy load 报 MissingGreenlet
        .options(selectinload(NewsArticle.source))
        .order_by(recency.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _degraded_content(articles: list[NewsArticle], domain: NewsDomain, digest_date) -> NewsDigestContent:
    """LLM 不可用时的降级稿：不做任何摘要，直出原始标题列表。"""
    return NewsDigestContent(
        title=f"{DOMAIN_LABELS[domain]}日报 · {digest_date.strftime('%m月%d日')}（降级）",
        summary="AI 摘要暂时不可用，以下为今日抓取到的原始文章，可点击标题查看原文。",
        items=[
            NewsDigestItem(
                headline=article.title,
                url=article.url,
                source_name=article.source.name if article.source else "",
                importance=0.0,
                published_at=article.published_at,
            )
            for article in articles[:MAX_DIGEST_ITEMS]
        ],
    )


async def _upsert_digest(
    db: AsyncSession,
    digest_date,
    domain: NewsDomain,
    content: NewsDigestContent,
    article_count: int,
    degraded: bool,
) -> NewsDigest:
    """(digest_date, domain) 唯一约束上的幂等写入：重复生成是覆盖，不新增行。"""
    result = await db.execute(
        select(NewsDigest).where(
            NewsDigest.digest_date == digest_date, NewsDigest.domain == domain
        )
    )
    digest = result.scalar_one_or_none()
    items = [item.model_dump(mode="json") for item in content.items]
    if digest is None:
        digest = NewsDigest(
            digest_date=digest_date,
            domain=domain,
            title=content.title[:200],
            summary=content.summary,
            items=items,
            article_count=article_count,
            degraded=degraded,
        )
        db.add(digest)
    else:
        digest.title = content.title[:200]
        digest.summary = content.summary
        digest.items = items
        digest.article_count = article_count
        digest.degraded = degraded
        db.add(digest)
    await db.commit()
    await db.refresh(digest)
    return digest


async def generate_digest(
    db: AsyncSession, domain: NewsDomain, digest_date=None
) -> NewsDigest | None:
    """为一个板块生成当日日报；窗口内没有文章时返回 None（调用方记录跳过）。"""
    settings = get_settings()
    if digest_date is None:
        digest_date = datetime.now(FIXED_TZ).date()

    articles = await _load_articles_for_digest(
        db,
        domain,
        digest_date,
        window_hours=settings.news_article_window_hours,
        limit=settings.news_max_articles_per_digest,
    )
    if not articles:
        logger.info("板块 %s %s 窗口内无文章，跳过日报生成", domain.value, digest_date)
        return None

    payload = {
        "domain_label": DOMAIN_LABELS[domain],
        "digest_date": digest_date.strftime("%m月%d日"),
        "max_items": MAX_DIGEST_ITEMS,
        "articles": [
            {
                "title": article.title,
                "source_name": article.source.name if article.source else "",
                "url": article.url,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                # 2026-10-03 送 LLM 的摘要截到 150 字（库里仍存 300 字供原始流展示）：
                # 40 篇 × 300 字的 prompt 会让 reasoning 模型的思考量暴涨、挤爆
                # max_tokens 预算，出现 content 空返或 JSON 截断
                "excerpt": (article.excerpt or "")[:150],
            }
            for article in articles
        ],
    }

    degraded = False
    try:
        raw = await asyncio.wait_for(
            llm.generate_news_digest(payload),
            timeout=settings.news_digest_llm_timeout_seconds,
        )
        content = NewsDigestContent.model_validate(raw)
        # 2026-10-03 标题由服务端拼，不采信 LLM 输出：实测模型会把科技/国际/财经
        # 等所有板块的 title 都写成「AI 日报 · x月x日」（无视 domain_label），
        # 板块名+日期服务端本来就确定，没有让模型自由发挥的理由
        content.title = f"{DOMAIN_LABELS[domain]}日报 · {digest_date.strftime('%m月%d日')}"
    except (TimeoutError, OpenAIError, ValidationError, ValueError) as exc:
        logger.warning(
            "日报 LLM 降级 %s %s：%s", domain.value, digest_date, type(exc).__name__
        )
        content = _degraded_content(articles, domain, digest_date)
        degraded = True

    return await _upsert_digest(
        db, digest_date, domain, content, article_count=len(articles), degraded=degraded
    )


async def generate_all_digests(digest_date=None) -> list[NewsDigest]:
    """六个板块各生成一份（每日定时任务与手动「生成今日日报」共用）。

    每个板块在独立子 session 里跑：AsyncSession 不是协程安全的，
    六个板块共用一个 session gather 会交叉污染事务。
    2026-10-03 并发度收紧到 2：六板块全并发时 StepFun 会对部分请求限流，
    LLM 直接返回空 content 走降级稿（实测 6 并发 3 个降级）。reasoning 模型
    单次调用本就 30-60 秒，2 路并发只慢一倍不到，换来全部板块正常出稿。
    """
    gate = asyncio.Semaphore(2)

    async def run_one(domain: NewsDomain):
        async with gate:
            async with async_session_factory() as session:
                try:
                    return await generate_digest(session, domain, digest_date)
                except Exception:
                    logger.exception("板块 %s 日报生成异常", domain.value)
                    return None

    results = await asyncio.gather(*(run_one(domain) for domain in NewsDomain))
    return [digest for digest in results if digest is not None]


# ---------- 来源管理 CRUD ----------


async def list_sources(db: AsyncSession) -> list[NewsSource]:
    result = await db.execute(
        select(NewsSource).order_by(NewsSource.domain, NewsSource.created_at)
    )
    return list(result.scalars().all())


async def get_source(db: AsyncSession, source_id) -> NewsSource | None:
    return await db.get(NewsSource, source_id)


async def create_source(db: AsyncSession, payload: NewsSourceCreate) -> NewsSource:
    source = NewsSource(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def update_source(
    db: AsyncSession, source: NewsSource, payload: NewsSourceUpdate
) -> NewsSource:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def delete_source(db: AsyncSession, source: NewsSource) -> None:
    await db.delete(source)
    await db.commit()


# ---------- 日报 / 文章查询 ----------


async def list_digests(
    db: AsyncSession, domain: NewsDomain | None, page: int, page_size: int
) -> tuple[list[NewsDigest], int]:
    filters = [] if domain is None else [NewsDigest.domain == domain]
    total = (
        await db.scalar(select(func.count()).select_from(NewsDigest).where(*filters)) or 0
    )
    result = await db.execute(
        select(NewsDigest)
        .where(*filters)
        .order_by(NewsDigest.digest_date.desc(), NewsDigest.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return list(result.scalars().all()), total


async def get_digest(db: AsyncSession, digest_id) -> NewsDigest | None:
    return await db.get(NewsDigest, digest_id)


async def list_articles(
    db: AsyncSession, domain: NewsDomain | None, page: int, page_size: int
) -> tuple[list[NewsArticle], int]:
    filters = [] if domain is None else [NewsArticle.domain == domain]
    total = (
        await db.scalar(select(func.count()).select_from(NewsArticle).where(*filters)) or 0
    )
    recency = func.coalesce(NewsArticle.published_at, NewsArticle.created_at)
    result = await db.execute(
        select(NewsArticle)
        .where(*filters)
        .options(selectinload(NewsArticle.source))
        .order_by(recency.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return list(result.scalars().all()), total
