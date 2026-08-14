from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.capture import router as capture_router
from app.api.v1.path import router as path_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(capture_router)
api_router.include_router(path_router)
