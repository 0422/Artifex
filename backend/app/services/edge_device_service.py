"""边缘设备管理模块业务逻辑。

职责划分：
  - 设备档案 CRUD（元数据由用户手动维护）
  - 局域网 UDP 扫描：把广播 IP 与档案对应，判定在线状态、挑出未认领 IP
  - 固件仓库：落盘 + sha256 校验
  - OTA 任务：状态机 + 后台执行 + 分片进度回写
  - WiFi / LLM / Prompt 配置下发

扫描结果不建表：scan 接口直接返回「已建档设备的在线情况 + 未认领 IP」视图，
由前端持有；作为副作用把设备的 status / last_online_at 落到库里。
"""

import hashlib
import ipaddress
import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.constants import EDGE_DEVICE_CHIPS, EDGE_DEFAULT_PROMPT
from app.core.database import async_session_factory
from app.models.edge_device import EdgeDevice, EdgeFirmware, EdgeOtaTask
from app.models.enums import EdgeDeviceStatus, EdgeOtaTaskStatus
from app.schemas.edge_device import is_masked
from app.services.edge_device_drivers import DeviceCommandError, DeviceDriver, get_driver
from app.services.edge_device_scanner import (
    DEFAULT_BROADCAST_PORT,
    ScanUnavailableError,
    scan_udp_broadcast,
)

logger = logging.getLogger(__name__)

_SHA256_CHUNK = 1024 * 1024

# 2026-09-30 新增边缘设备管理模块：允许上传的固件扩展名。
# ESP-IDF 产物为 .bin，RK3576 走 Linux 镜像故放开 .img / .elf。
_ALLOWED_FIRMWARE_SUFFIXES = {".bin", ".img", ".elf"}


class DeviceNotFoundError(LookupError):
    pass


class FirmwareError(ValueError):
    """固件上传/读取阶段的校验失败。"""


# ---------------------------------------------------------------------------
# 设备档案
# ---------------------------------------------------------------------------


async def list_devices(db: AsyncSession, user_id: uuid.UUID) -> list[EdgeDevice]:
    result = await db.execute(
        select(EdgeDevice)
        .where(EdgeDevice.user_id == user_id)
        .order_by(EdgeDevice.created_at)
    )
    return list(result.scalars().all())


async def get_device(
    db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID
) -> EdgeDevice:
    device = await db.get(EdgeDevice, device_id)
    if device is None or device.user_id != user_id:
        raise DeviceNotFoundError("设备不存在")
    return device


async def create_device(
    db: AsyncSession, user_id: uuid.UUID, payload
) -> EdgeDevice:
    ip = payload.ip_address
    if ip is not None:
        _validate_device_ip(ip)

    device = EdgeDevice(
        user_id=user_id,
        name=payload.name.strip(),
        chip=payload.chip.strip(),
        ip_address=ip,
        mac_address=payload.mac_address,
        firmware_version=payload.firmware_version,
        notes=payload.notes,
        status=EdgeDeviceStatus.UNKNOWN,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def update_device(
    db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID, payload
) -> EdgeDevice:
    device = await get_device(db, user_id, device_id)
    data = payload.model_dump(exclude_unset=True)

    if "ip_address" in data and data["ip_address"] is not None:
        _validate_device_ip(data["ip_address"])

    for field in ("name", "chip", "ip_address", "mac_address", "firmware_version", "notes"):
        if field in data:
            setattr(device, field, data[field])

    await db.commit()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID) -> None:
    device = await get_device(db, user_id, device_id)
    await db.delete(device)
    await db.commit()


def _validate_device_ip(ip: str) -> None:
    """建档阶段就拒绝非法 IP，避免把不可达的地址写进档案。"""
    try:
        ipaddress.ip_address(ip)
    except ValueError as exc:
        raise ValueError(f"非法的设备 IP：{ip}") from exc


# ---------------------------------------------------------------------------
# 局域网扫描
# ---------------------------------------------------------------------------


async def run_scan(
    db: AsyncSession, user_id: uuid.UUID, timeout: float | None = None
) -> dict:
    """扫描局域网广播设备，并把结果与用户档案对应。

    返回未序列化的原始数据，由路由层转成 ScanResult。
    ScanUnavailableError 向上抛给路由层转 503。
    """
    settings = get_settings()
    port = settings.edge_udp_port or DEFAULT_BROADCAST_PORT
    window = settings.edge_scan_timeout if timeout is None else timeout

    started = datetime.now()
    hits = await scan_udp_broadcast(port, window)
    duration_ms = int((datetime.now() - started).total_seconds() * 1000)

    hit_by_ip = {hit.ip: hit for hit in hits}
    devices = await list_devices(db, user_id)
    now = datetime.now()

    matched: list[dict] = []
    online_ips: set[str] = set()
    for device in devices:
        hit = hit_by_ip.get(device.ip_address) if device.ip_address else None
        if hit is not None:
            online_ips.add(hit.ip)
            device.status = EdgeDeviceStatus.ONLINE
            device.last_online_at = now
        else:
            device.status = EdgeDeviceStatus.OFFLINE
        matched.append(
            {
                "device_id": device.id,
                "name": device.name,
                "ip_address": device.ip_address,
                "online": hit is not None,
                "payload": hit.payload if hit else None,
            }
        )

    await db.commit()

    unclaimed = [
        {"ip": hit.ip, "payload": hit.payload, "seen_count": hit.seen_count}
        for hit in hits
        if hit.ip not in online_ips
    ]

    return {
        "scanned_at": started,
        "duration_ms": duration_ms,
        "port": port,
        "unclaimed": unclaimed,
        "matched": matched,
    }


# ---------------------------------------------------------------------------
# 固件仓库
# ---------------------------------------------------------------------------


def _firmware_root() -> Path:
    settings = get_settings()
    root = Path(settings.edge_firmware_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_SHA256_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


async def save_firmware(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    filename: str,
    content: bytes,
    version: str,
    chip: str,
    notes: str | None = None,
) -> EdgeFirmware:
    """把上传的固件落盘并记录 sha256。校验失败时不留残留文件。"""
    settings = get_settings()
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_FIRMWARE_SUFFIXES:
        raise FirmwareError(
            f"不支持的固件格式 {suffix or '(无扩展名)'}，仅接受 "
            f"{' / '.join(sorted(_ALLOWED_FIRMWARE_SUFFIXES))}"
        )
    if not content:
        raise FirmwareError("固件文件为空")
    if len(content) > settings.edge_firmware_max_mb * 1024 * 1024:
        raise FirmwareError(
            f"固件超过大小上限 {settings.edge_firmware_max_mb} MB"
        )
    if chip not in EDGE_DEVICE_CHIPS:
        raise FirmwareError(
            f"不支持的芯片型号 {chip}，可选：{' / '.join(EDGE_DEVICE_CHIPS)}"
        )

    root = _firmware_root()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = root / stored_name
    target.write_bytes(content)

    try:
        sha256 = _sha256_of(target)
    except OSError:
        target.unlink(missing_ok=True)
        raise

    firmware = EdgeFirmware(
        user_id=user_id,
        filename=filename,
        version=version.strip(),
        chip=chip,
        size_bytes=len(content),
        sha256=sha256,
        file_path=str(target.relative_to(root.parent)),
        notes=notes,
    )
    db.add(firmware)
    await db.commit()
    await db.refresh(firmware)
    return firmware


async def list_firmware(db: AsyncSession, user_id: uuid.UUID) -> list[EdgeFirmware]:
    result = await db.execute(
        select(EdgeFirmware)
        .where(EdgeFirmware.user_id == user_id)
        .order_by(EdgeFirmware.created_at.desc())
    )
    return list(result.scalars().all())


async def get_firmware(
    db: AsyncSession, user_id: uuid.UUID, firmware_id: uuid.UUID
) -> EdgeFirmware:
    firmware = await db.get(EdgeFirmware, firmware_id)
    if firmware is None or firmware.user_id != user_id:
        raise FirmwareError("固件不存在")
    return firmware


async def delete_firmware(
    db: AsyncSession, user_id: uuid.UUID, firmware_id: uuid.UUID
) -> None:
    firmware = await get_firmware(db, user_id, firmware_id)
    path = Path(firmware.file_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    # 引用它的 OTA 任务依赖 ondelete=SET NULL，删文件不会破坏历史记录
    await db.delete(firmware)
    await db.commit()
    path.unlink(missing_ok=True)


def resolve_firmware_path(firmware: EdgeFirmware) -> Path:
    path = Path(firmware.file_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path


# ---------------------------------------------------------------------------
# OTA 任务
# ---------------------------------------------------------------------------


async def list_ota_tasks(
    db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID | None = None
) -> list[EdgeOtaTask]:
    stmt = select(EdgeOtaTask).where(EdgeOtaTask.user_id == user_id)
    if device_id is not None:
        stmt = stmt.where(EdgeOtaTask.device_id == device_id)
    result = await db.execute(stmt.order_by(EdgeOtaTask.created_at.desc()))
    return list(result.scalars().all())


async def get_ota_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> EdgeOtaTask:
    task = await db.get(EdgeOtaTask, task_id)
    if task is None or task.user_id != user_id:
        raise DeviceNotFoundError("OTA 任务不存在")
    return task


async def create_ota_task(
    db: AsyncSession,
    user_id: uuid.UUID,
    device_id: uuid.UUID,
    payload,
) -> EdgeOtaTask:
    """建档一条 pending 任务。真正的推送由路由层用 BackgroundTasks 触发。"""
    device = await get_device(db, user_id, device_id)
    if not device.ip_address:
        raise ValueError("设备尚未设置 IP，无法推送固件")
    await get_firmware(db, user_id, payload.firmware_id)

    task = EdgeOtaTask(
        user_id=user_id,
        device_id=device.id,
        firmware_id=payload.firmware_id,
        status=EdgeOtaTaskStatus.PENDING,
        progress=0,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def cancel_ota_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> EdgeOtaTask:
    task = await get_ota_task(db, user_id, task_id)
    if task.status in (EdgeOtaTaskStatus.SUCCESS, EdgeOtaTaskStatus.FAILED):
        raise ValueError("任务已结束，无法取消")
    task.status = EdgeOtaTaskStatus.CANCELED
    task.finished_at = datetime.now()
    task.log = _append_log(task.log, "用户取消了任务")
    await db.commit()
    await db.refresh(task)
    return task


async def run_ota_task(
    task_id: uuid.UUID,
    *,
    driver: DeviceDriver | None = None,
    session_factory: async_sessionmaker | None = None,
) -> None:
    """后台执行 OTA 推送，持续把进度与日志写库。

    自建 DB 会话（同 capture_service.process_capture 的做法），与请求生命周期解耦，
    这样 BackgroundTasks 触发后前端可以独立轮询任务详情看进度。
    """
    factory = session_factory or async_session_factory

    async with factory() as db:
        task = await db.get(EdgeOtaTask, task_id)
        # 状态检查要放在取 driver 之前：已取消/已结束的任务不该再实例化驱动
        if task is None or task.status != EdgeOtaTaskStatus.PENDING:
            return

        active_driver = driver or get_driver()

        device = await db.get(EdgeDevice, task.device_id)
        firmware = await db.get(EdgeFirmware, task.firmware_id) if task.firmware_id else None
        if device is None or firmware is None or not device.ip_address:
            await _finish_task(db, task, EdgeOtaTaskStatus.FAILED, error="设备或固件信息不完整")
            return

        task.status = EdgeOtaTaskStatus.RUNNING
        task.started_at = datetime.now()
        task.log = _append_log(task.log, f"开始向 {device.name}（{device.ip_address}）推送固件 {firmware.version}")
        await db.commit()

        async def _on_progress(value: int) -> None:
            # 推送过程中被取消则停止回写进度，让后台循环尽快收敛
            if task.status != EdgeOtaTaskStatus.RUNNING:
                return
            task.progress = max(0, min(100, value))
            await db.commit()

        try:
            path = resolve_firmware_path(firmware)
            await active_driver.push_firmware(
                device.ip_address, str(path), on_progress=_on_progress
            )
        except DeviceCommandError as exc:
            # 设备不支持 / 不可达 / 拒绝：把错误码与说明都落库，前端据此给中文提示
            task.log = _append_log(task.log, f"失败：{exc.message}")
            await _finish_task(db, task, EdgeOtaTaskStatus.FAILED, error=f"{exc.code}: {exc.message}")
            return
        except Exception as exc:  # noqa: BLE001 - 后台任务必须兜住异常改写状态
            logger.exception("OTA 任务 %s 执行异常", task_id)
            task.log = _append_log(task.log, f"异常：{exc}")
            await _finish_task(db, task, EdgeOtaTaskStatus.FAILED, error=f"unexpected-error: {exc}")
            return

        task.log = _append_log(task.log, "固件推送完成，等待设备重启生效")
        await _finish_task(db, task, EdgeOtaTaskStatus.SUCCESS)


async def _finish_task(
    db: AsyncSession,
    task: EdgeOtaTask,
    status: EdgeOtaTaskStatus,
    *,
    error: str | None = None,
) -> None:
    # 用户在推送过程中点了取消：后台线程随后跑完也不能把状态改回 success/failed，
    # 否则界面上会显示一个"成功完成"的已取消任务。
    if task.status == EdgeOtaTaskStatus.CANCELED:
        return

    task.status = status
    task.finished_at = datetime.now()
    if error:
        task.error = error
    if status is EdgeOtaTaskStatus.SUCCESS:
        task.progress = 100
    await db.commit()


def _append_log(existing: str | None, line: str) -> str:
    stamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{stamp}] {line}"
    return f"{existing}\n{entry}" if existing else entry


# ---------------------------------------------------------------------------
# 配置下发
# ---------------------------------------------------------------------------


async def push_wifi(
    db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID, payload
) -> EdgeDevice:
    device = await get_device(db, user_id, device_id)
    if not device.ip_address:
        raise ValueError("设备尚未设置 IP，无法下发配置")

    await get_driver().push_wifi(device.ip_address, payload.ssid, payload.password)
    # 设备侧处理成功后镜像一份到档案，便于在管理端回看各设备当前用什么网络
    device.wifi_ssid = payload.ssid
    await db.commit()
    await db.refresh(device)
    return device


async def push_llm_config(
    db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID, payload
) -> EdgeDevice:
    device = await get_device(db, user_id, device_id)
    if not device.ip_address:
        raise ValueError("设备尚未设置 IP，无法下发配置")

    # 前端回显的是脱敏后的 key；若用户没改成新值，沿用库里已有的那把，
    # 否则会把 "****abcd" 当成真 key 写进设备。
    config = payload.model_dump(exclude_none=True)
    existing = device.llm_config or {}
    if is_masked(config.get("api_key")):
        config.pop("api_key", None)
        if existing.get("api_key"):
            config["api_key"] = existing["api_key"]

    await get_driver().push_llm_config(device.ip_address, config)

    merged = {**existing, **config}
    device.llm_config = merged
    await db.commit()
    await db.refresh(device)
    return device


async def push_prompt(
    db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID, payload
) -> EdgeDevice:
    device = await get_device(db, user_id, device_id)
    if not device.ip_address:
        raise ValueError("设备尚未设置 IP，无法下发配置")

    prompt = payload.system_prompt.strip()
    await get_driver().push_prompt(device.ip_address, prompt)

    device.prompt_config = {"system_prompt": prompt}
    await db.commit()
    await db.refresh(device)
    return device


def default_prompt() -> str:
    return EDGE_DEFAULT_PROMPT
