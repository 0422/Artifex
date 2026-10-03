import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.services import news_service

logger = logging.getLogger(__name__)

# 2026-10-03 新增世势洞察（M6）调度器：挂在 FastAPI lifespan 上的 APScheduler。
# 选型理由：celery[redis] 虽在 pyproject 里，但从未起过 worker（M1 阶段文档明确
# 因 Windows 兼容性放弃过），本机单进程部署没必要为一个定时任务引入两个常驻进程。
# 两个 job：
#   fetch_news     每 N 分钟抓一轮所有启用源
#   generate_news_digests  每日固定时刻给六个板块各生成一份日报
# 每个 job 用 async_session_factory 开独立 session，不复用请求级 get_db。

_scheduler: AsyncIOScheduler | None = None


async def _run_fetch_job() -> None:
    async with async_session_factory() as session:
        try:
            result = await news_service.fetch_all_sources(session)
            logger.info(
                "定时抓取完成：源 %d，成功 %d，失败 %d，新文章 %d",
                result["total_sources"],
                result["succeeded"],
                result["failed"],
                result["new_articles"],
            )
        except Exception:
            # 调度任务绝不能把异常漏到 scheduler 事件循环里，否则 job 状态卡在异常
            logger.exception("定时抓取任务异常")


async def _run_digest_job() -> None:
    # generate_all_digests 内部自建子 session，这里不需要再包 session
    try:
        digests = await news_service.generate_all_digests()
        logger.info("定时日报完成：生成 %d 份", len(digests))
    except Exception:
        logger.exception("定时日报任务异常")


async def start_scheduler() -> None:
    """启动调度器。幂等：已启动（uvicorn --reload 重启场景）时直接跳过。"""
    global _scheduler
    settings = get_settings()
    if _scheduler is not None and _scheduler.running:
        logger.info("新闻调度器已在运行，跳过重复启动")
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_fetch_job,
        IntervalTrigger(minutes=settings.news_fetch_interval_minutes),
        id="news_fetch",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _run_digest_job,
        # 时区用固定 UTC+8（与 news_service.FIXED_TZ 保持一致）：
        # Windows 无系统 tz 数据库，APScheduler 默认找不到 Asia/Shanghai 会静默失效
        CronTrigger(
            hour=settings.news_digest_hour,
            minute=3,
            timezone=news_service.FIXED_TZ,
        ),
        id="news_digest",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "新闻调度器已启动（抓取间隔 %d 分钟，日报时刻 %02d:03 UTC+8）",
        settings.news_fetch_interval_minutes,
        settings.news_digest_hour,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("新闻调度器已停止")
