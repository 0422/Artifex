from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import get_settings
# 2026-10-03 世势洞察（M6）模块：新闻抓取/日报生成调度器
from app.workers import news_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化连接池、加载模型
    # 2026-10-03 世势洞察调度器随 lifespan 启停；关闭时显式 shutdown，
    # 否则 uvicorn --reload 重启 worker 会叠加出第二个 scheduler
    if settings.news_scheduler_enabled:
        await news_scheduler.start_scheduler()
    yield
    # 关闭时：释放连接
    news_scheduler.shutdown_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS（开发阶段放开，生产收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}
