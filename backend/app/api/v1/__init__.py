from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.dashboard import router as dashboard_router
# 2026-09-30 新增边缘设备管理模块
from app.api.v1.edge_device import router as edge_device_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.llm import router as llm_router
from app.api.v1.scenarios import router as scenarios_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(dashboard_router)
api_router.include_router(edge_device_router)
api_router.include_router(knowledge_router)
api_router.include_router(llm_router)
api_router.include_router(scenarios_router)
