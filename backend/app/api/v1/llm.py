from fastapi import APIRouter, Depends, HTTPException, status

from app.ai import llm_config
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.llm import (
    LLMActivateRequest,
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProvidersResponse,
)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/providers", response_model=LLMProvidersResponse)
async def read_providers(current_user: User = Depends(get_current_user)) -> LLMProvidersResponse:
    """列出所有 LLM 供应商及其模型（API Key 脱敏）。"""
    return LLMProvidersResponse.model_validate(llm_config.list_providers())


@router.post("/providers", response_model=LLMProvidersResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: LLMProviderCreate,
    current_user: User = Depends(get_current_user),
) -> LLMProvidersResponse:
    """新增一家 LLM 供应商及其模型，写入配置文件。"""
    try:
        data = llm_config.add_provider(
            payload.name, payload.base_url, payload.api_key, payload.models
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LLMProvidersResponse.model_validate(data)


@router.post("/providers/{provider_id}/activate", response_model=LLMProvidersResponse)
async def activate_provider(
    provider_id: str,
    payload: LLMActivateRequest,
    current_user: User = Depends(get_current_user),
) -> LLMProvidersResponse:
    """切换当前使用的 LLM 供应商，可同时指定模型。"""
    try:
        data = llm_config.set_active(provider_id, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LLMProvidersResponse.model_validate(data)


@router.put("/providers/{provider_id}", response_model=LLMProvidersResponse)
async def update_provider(
    provider_id: str,
    payload: LLMProviderUpdate,
    current_user: User = Depends(get_current_user),
) -> LLMProvidersResponse:
    """修改已有供应商；api_key 留空表示不修改。内置供应商同样可改（仅不可删除）。"""
    try:
        data = llm_config.update_provider(
            provider_id,
            name=payload.name,
            base_url=payload.base_url,
            api_key=payload.api_key,
            models=[m.model_dump() for m in payload.models] if payload.models is not None else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LLMProvidersResponse.model_validate(data)


@router.delete("/providers/{provider_id}", response_model=LLMProvidersResponse)
async def remove_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
) -> LLMProvidersResponse:
    """删除用户自建供应商；内置供应商不可删除。"""
    try:
        data = llm_config.delete_provider(provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LLMProvidersResponse.model_validate(data)
