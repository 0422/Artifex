from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.capture import router as capture_router
from app.api.v1.chat import router as chat_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.path import router as path_router
from app.api.v1.scenarios import router as scenarios_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(capture_router)
api_router.include_router(chat_router)
api_router.include_router(dashboard_router)
api_router.include_router(knowledge_router)
api_router.include_router(path_router)
api_router.include_router(scenarios_router)
