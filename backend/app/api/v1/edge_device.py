import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.constants import EDGE_DEVICE_CHIPS
from app.core.database import get_db
from app.models.user import User
from app.schemas.edge_device import (
    EdgeDeviceCreate,
    EdgeDeviceRead,
    EdgeDeviceUpdate,
    EdgeFirmwareRead,
    EdgeOtaTaskCreate,
    EdgeOtaTaskRead,
    EdgePromptInput,
    EdgeWifiInput,
    LlmConfig,
    ScanResult,
)
from app.services import edge_device_service
from app.services.edge_device_drivers import DeviceCommandError
from app.services.edge_device_scanner import ScanUnavailableError

router = APIRouter(prefix="/edge-devices", tags=["edge-devices"])

# 2026-09-30 新增边缘设备管理模块：静态路径必须在 /{device_id} 之前声明，
# 否则 scan / firmware / ota-tasks 会被当成 UUID 路径参数匹配。
# 因此本文件把设备 CRUD 之外的端点集中放在前面。


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ---------------------------------------------------------------------------
# 局域网扫描
# ---------------------------------------------------------------------------


@router.post("/scan", response_model=ScanResult)
async def scan_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanResult:
    """扫描局域网广播设备，返回未认领 IP 与已建档设备的在线情况。"""
    try:
        result = await edge_device_service.run_scan(db, current_user.id)
    except ScanUnavailableError as exc:
        # 端口绑定失败是运行环境问题（端口被占用/无权限），语义上接近服务不可用
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return ScanResult.model_validate(result)


@router.get("/default-prompt")
async def get_default_prompt() -> dict[str, str]:
    """前端「恢复默认模板」按钮取这份文案。"""
    return {"system_prompt": edge_device_service.default_prompt()}


# ---------------------------------------------------------------------------
# 固件仓库
# ---------------------------------------------------------------------------


@router.get("/firmware", response_model=list[EdgeFirmwareRead])
async def list_firmware(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EdgeFirmwareRead]:
    firmware = await edge_device_service.list_firmware(db, current_user.id)
    return [EdgeFirmwareRead.model_validate(item) for item in firmware]


@router.post(
    "/firmware",
    response_model=EdgeFirmwareRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_firmware(
    version: str = Form(...),
    chip: str = Form(...),
    file: UploadFile = File(...),
    notes: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeFirmwareRead:
    """上传编译好的固件二进制到本地仓库（算 sha256 并落盘）。"""
    content = await file.read()
    try:
        firmware = await edge_device_service.save_firmware(
            db,
            current_user.id,
            filename=file.filename or "firmware.bin",
            content=content,
            version=version,
            chip=chip,
            notes=notes,
        )
    except edge_device_service.FirmwareError as exc:
        raise _bad_request(exc) from exc
    return EdgeFirmwareRead.model_validate(firmware)


@router.delete("/firmware/{firmware_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_firmware(
    firmware_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await edge_device_service.delete_firmware(db, current_user.id, firmware_id)


# ---------------------------------------------------------------------------
# OTA 任务
# ---------------------------------------------------------------------------


@router.get("/ota-tasks", response_model=list[EdgeOtaTaskRead])
async def list_ota_tasks(
    device_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EdgeOtaTaskRead]:
    tasks = await edge_device_service.list_ota_tasks(db, current_user.id, device_id)
    return [EdgeOtaTaskRead.model_validate(task) for task in tasks]


@router.get("/ota-tasks/{task_id}", response_model=EdgeOtaTaskRead)
async def get_ota_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeOtaTaskRead:
    try:
        task = await edge_device_service.get_ota_task(db, current_user.id, task_id)
    except edge_device_service.DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EdgeOtaTaskRead.model_validate(task)


@router.post(
    "/{device_id}/ota-tasks",
    response_model=EdgeOtaTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ota_task(
    device_id: uuid.UUID,
    payload: EdgeOtaTaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeOtaTaskRead:
    """创建 OTA 任务并立即在后台开始推送。"""
    try:
        task = await edge_device_service.create_ota_task(
            db, current_user.id, device_id, payload
        )
    except (ValueError, edge_device_service.DeviceNotFoundError) as exc:
        raise _bad_request(exc) from exc

    background_tasks.add_task(edge_device_service.run_ota_task, task.id)
    return EdgeOtaTaskRead.model_validate(task)


@router.post("/ota-tasks/{task_id}/cancel", response_model=EdgeOtaTaskRead)
async def cancel_ota_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeOtaTaskRead:
    """取消尚未结束的任务。已在推送中的分片会在下次进度回写前自然收敛。"""
    try:
        task = await edge_device_service.cancel_ota_task(db, current_user.id, task_id)
    except (ValueError, edge_device_service.DeviceNotFoundError) as exc:
        raise _bad_request(exc) from exc
    return EdgeOtaTaskRead.model_validate(task)


# ---------------------------------------------------------------------------
# 设备档案
# ---------------------------------------------------------------------------


@router.get("", response_model=list[EdgeDeviceRead])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EdgeDeviceRead]:
    devices = await edge_device_service.list_devices(db, current_user.id)
    return [EdgeDeviceRead.model_validate(device) for device in devices]


@router.post("", response_model=EdgeDeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: EdgeDeviceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeDeviceRead:
    try:
        device = await edge_device_service.create_device(db, current_user.id, payload)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return EdgeDeviceRead.model_validate(device)


@router.get("/{device_id}", response_model=EdgeDeviceRead)
async def get_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeDeviceRead:
    try:
        device = await edge_device_service.get_device(db, current_user.id, device_id)
    except edge_device_service.DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return EdgeDeviceRead.model_validate(device)


@router.patch("/{device_id}", response_model=EdgeDeviceRead)
async def update_device(
    device_id: uuid.UUID,
    payload: EdgeDeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeDeviceRead:
    try:
        device = await edge_device_service.update_device(
            db, current_user.id, device_id, payload
        )
    except (ValueError, edge_device_service.DeviceNotFoundError) as exc:
        raise _bad_request(exc) from exc
    return EdgeDeviceRead.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await edge_device_service.delete_device(db, current_user.id, device_id)


# ---------------------------------------------------------------------------
# 配置下发
# ---------------------------------------------------------------------------


async def _push_config(action) -> EdgeDeviceRead:
    """配置下发的统一错误翻译。

    DeviceCommandError -> 502（设备侧问题，非服务端故障）；
    DeviceNotFoundError -> 404；参数问题 -> 400。
    """
    try:
        return await action()
    except edge_device_service.DeviceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DeviceCommandError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{exc.code}: {exc.message}"
        ) from exc
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.put("/{device_id}/wifi", response_model=EdgeDeviceRead)
async def push_wifi(
    device_id: uuid.UUID,
    payload: EdgeWifiInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeDeviceRead:
    return await _push_config(
        lambda: edge_device_service.push_wifi(db, current_user.id, device_id, payload)
    )


@router.put("/{device_id}/llm-config", response_model=EdgeDeviceRead)
async def push_llm_config(
    device_id: uuid.UUID,
    payload: LlmConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeDeviceRead:
    return await _push_config(
        lambda: edge_device_service.push_llm_config(db, current_user.id, device_id, payload)
    )


@router.put("/{device_id}/prompt", response_model=EdgeDeviceRead)
async def push_prompt(
    device_id: uuid.UUID,
    payload: EdgePromptInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EdgeDeviceRead:
    return await _push_config(
        lambda: edge_device_service.push_prompt(db, current_user.id, device_id, payload)
    )
