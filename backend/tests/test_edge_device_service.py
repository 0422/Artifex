import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import EdgeDeviceStatus, EdgeOtaTaskStatus
from app.schemas.edge_device import (
    EdgeDeviceCreate,
    EdgeDeviceRead,
    EdgePromptInput,
    EdgeWifiInput,
    LlmConfig,
    is_masked,
)
from app.services import edge_device_service
from app.services.edge_device_drivers import DeviceCommandError


# ---------------------------------------------------------------------------
# api_key 脱敏：落库是明文，读取一律不回传
# ---------------------------------------------------------------------------


def test_llm_config_masks_real_api_key() -> None:
    read = EdgeDeviceRead(
        id=uuid.uuid4(),
        name="书桌助手",
        chip="esp32s3",
        ip_address="192.168.1.42",
        mac_address=None,
        firmware_version="3.0.1",
        status=EdgeDeviceStatus.ONLINE,
        last_online_at=datetime.now(UTC),
        wifi_ssid=None,
        llm_config={"api_key": "sk-real-secret-abcd1234", "model": "gpt-4o"},
        prompt_config=None,
        notes=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert read.llm_config is not None
    assert read.llm_config.api_key == "****1234"
    assert "sk-real-secret" not in str(read.model_dump())


def test_llm_config_keeps_other_fields_when_masking() -> None:
    read = EdgeDeviceRead(
        id=uuid.uuid4(),
        name="书桌助手",
        chip="esp32s3",
        ip_address=None,
        mac_address=None,
        firmware_version=None,
        status=EdgeDeviceStatus.UNKNOWN,
        last_online_at=None,
        wifi_ssid=None,
        llm_config={"api_key": "sk-abcd1234", "base_url": "https://api.example.com"},
        prompt_config=None,
        notes=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert read.llm_config is not None
    assert read.llm_config.base_url == "https://api.example.com"


def test_llm_config_handles_short_key() -> None:
    read = EdgeDeviceRead(
        id=uuid.uuid4(),
        name="d",
        chip="esp32s3",
        ip_address=None,
        mac_address=None,
        firmware_version=None,
        status=EdgeDeviceStatus.UNKNOWN,
        last_online_at=None,
        wifi_ssid=None,
        llm_config={"api_key": "abc"},
        prompt_config=None,
        notes=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert read.llm_config is not None
    assert read.llm_config.api_key == "****"


@pytest.mark.parametrize(
    "value",
    [None, "", "   ", "****", "****1234"],
)
def test_is_masked_detects_non_real_key(value: str | None) -> None:
    assert is_masked(value)


def test_is_masked_rejects_real_key() -> None:
    assert not is_masked("sk-real-secret-abcd")


# ---------------------------------------------------------------------------
# ILM 配置下发：脱敏回显不得覆盖库中真实 key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_llm_config_preserves_existing_key_when_masked() -> None:
    device_id = uuid.uuid4()
    device = SimpleNamespace(
        id=device_id,
        user_id=uuid.uuid4(),
        ip_address="192.168.1.42",
        llm_config={"api_key": "sk-real-secret-abcd", "model": "gpt-4o"},
        prompt_config=None,
    )
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(return_value=device)

    driver = MagicMock()
    driver.push_llm_config = AsyncMock()

    # 前端把脱敏值原样提交回来，服务层应保留库里那把真 key
    payload = LlmConfig(api_key="****abcd", base_url="https://new.example.com")

    with patch.object(edge_device_service, "get_driver", return_value=driver):
        await edge_device_service.push_llm_config(db, device.user_id, device_id, payload)

    assert driver.push_llm_config.await_args.args[1]["api_key"] == "sk-real-secret-abcd"
    assert driver.push_llm_config.await_args.args[1]["base_url"] == "https://new.example.com"
    assert device.llm_config["api_key"] == "sk-real-secret-abcd"


@pytest.mark.asyncio
async def test_push_llm_config_writes_new_key_when_provided() -> None:
    device_id = uuid.uuid4()
    device = SimpleNamespace(
        id=device_id,
        user_id=uuid.uuid4(),
        ip_address="192.168.1.42",
        llm_config={"api_key": "sk-old-key-1111"},
        prompt_config=None,
    )
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(return_value=device)

    driver = MagicMock()
    driver.push_llm_config = AsyncMock()

    payload = LlmConfig(api_key="sk-brand-new-2222")

    with patch.object(edge_device_service, "get_driver", return_value=driver):
        await edge_device_service.push_llm_config(db, device.user_id, device_id, payload)

    assert driver.push_llm_config.await_args.args[1]["api_key"] == "sk-brand-new-2222"
    assert device.llm_config["api_key"] == "sk-brand-new-2222"


@pytest.mark.asyncio
async def test_push_wifi_mirrors_ssid_to_profile() -> None:
    device_id = uuid.uuid4()
    device = SimpleNamespace(
        id=device_id, user_id=uuid.uuid4(), ip_address="192.168.1.42", wifi_ssid=None
    )
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(return_value=device)

    driver = MagicMock()
    driver.push_wifi = AsyncMock()

    with patch.object(edge_device_service, "get_driver", return_value=driver):
        await edge_device_service.push_wifi(
            db, device.user_id, device_id, EdgeWifiInput(ssid="HomeNet", password="pw")
        )

    assert device.wifi_ssid == "HomeNet"
    assert driver.push_wifi.await_args.args[1:] == ("HomeNet", "pw")


@pytest.mark.asyncio
async def test_push_prompt_stores_stripped_prompt() -> None:
    device_id = uuid.uuid4()
    device = SimpleNamespace(
        id=device_id, user_id=uuid.uuid4(), ip_address="192.168.1.42", prompt_config=None
    )
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(return_value=device)

    driver = MagicMock()
    driver.push_prompt = AsyncMock()

    with patch.object(edge_device_service, "get_driver", return_value=driver):
        await edge_device_service.push_prompt(
            db, device.user_id, device_id, EdgePromptInput(system_prompt="  你是助手  ")
        )

    assert device.prompt_config == {"system_prompt": "你是助手"}


@pytest.mark.asyncio
async def test_push_config_fails_without_ip() -> None:
    device_id = uuid.uuid4()
    device = SimpleNamespace(
        id=device_id, user_id=uuid.uuid4(), ip_address=None, wifi_ssid=None
    )
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(return_value=device)

    with pytest.raises(ValueError, match="IP"):
        await edge_device_service.push_wifi(
            db, device.user_id, device_id, EdgeWifiInput(ssid="S", password="p")
        )


# ---------------------------------------------------------------------------
# OTA 任务状态机
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_ota_task_success_updates_progress_to_100() -> None:
    task_id = uuid.uuid4()
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    firmware_id = uuid.uuid4()

    task = SimpleNamespace(
        id=task_id,
        user_id=user_id,
        device_id=device_id,
        firmware_id=firmware_id,
        status=EdgeOtaTaskStatus.PENDING,
        progress=0,
        log=None,
        error=None,
        started_at=None,
        finished_at=None,
    )
    device = SimpleNamespace(id=device_id, name="书桌助手", ip_address="192.168.1.42")
    firmware = SimpleNamespace(id=firmware_id, version="3.0.1", file_path="firmware/x.bin")

    responses = {task_id: task, device_id: device, firmware_id: firmware}
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, object_id: responses.get(object_id))
    db.commit = AsyncMock()

    driver = MagicMock()
    driver.push_firmware = AsyncMock()

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)

    with patch.object(edge_device_service, "get_driver", return_value=driver), \
         patch.object(edge_device_service, "resolve_firmware_path", return_value=Path("x.bin")), \
         patch.object(edge_device_service, "async_session_factory", return_value=session):
        await edge_device_service.run_ota_task(task_id)

    assert task.status == EdgeOtaTaskStatus.SUCCESS
    assert task.progress == 100
    assert task.finished_at is not None
    assert driver.push_firmware.await_count == 1


@pytest.mark.asyncio
async def test_run_ota_task_records_error_code_when_device_lacks_ota() -> None:
    task_id = uuid.uuid4()
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()
    firmware_id = uuid.uuid4()

    task = SimpleNamespace(
        id=task_id,
        user_id=user_id,
        device_id=device_id,
        firmware_id=firmware_id,
        status=EdgeOtaTaskStatus.PENDING,
        progress=0,
        log=None,
        error=None,
        started_at=None,
        finished_at=None,
    )
    device = SimpleNamespace(id=device_id, name="书桌助手", ip_address="192.168.1.42")
    firmware = SimpleNamespace(id=firmware_id, version="3.0.1", file_path="firmware/x.bin")

    responses = {task_id: task, device_id: device, firmware_id: firmware}
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, object_id: responses.get(object_id))
    db.commit = AsyncMock()

    driver = MagicMock()
    driver.push_firmware = AsyncMock(side_effect=DeviceCommandError(
        "device-ota-unsupported", "设备固件暂不支持 OTA"
    ))

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)

    with patch.object(edge_device_service, "get_driver", return_value=driver), \
         patch.object(edge_device_service, "resolve_firmware_path", return_value=Path("x.bin")), \
         patch.object(edge_device_service, "async_session_factory", return_value=session):
        await edge_device_service.run_ota_task(task_id)

    assert task.status == EdgeOtaTaskStatus.FAILED
    assert task.error.startswith("device-ota-unsupported:")
    assert "设备固件暂不支持 OTA" in task.error


@pytest.mark.asyncio
async def test_run_ota_task_does_not_overwrite_canceled_status() -> None:
    """推送途中用户取消：后台跑完后不得把状态改回 success。"""
    task_id = uuid.uuid4()
    device_id = uuid.uuid4()
    firmware_id = uuid.uuid4()

    task = SimpleNamespace(
        id=task_id,
        user_id=uuid.uuid4(),
        device_id=device_id,
        firmware_id=firmware_id,
        status=EdgeOtaTaskStatus.PENDING,
        progress=0,
        log=None,
        error=None,
        started_at=None,
        finished_at=None,
    )
    device = SimpleNamespace(id=device_id, name="书桌助手", ip_address="192.168.1.42")
    firmware = SimpleNamespace(id=firmware_id, version="3.0.1", file_path="firmware/x.bin")

    responses = {task_id: task, device_id: device, firmware_id: firmware}
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, object_id: responses.get(object_id))
    db.commit = AsyncMock()

    async def slow_push(ip, path, *, on_progress=None):
        # 模拟推送过程中用户点了取消
        task.status = EdgeOtaTaskStatus.CANCELED
        task.finished_at = datetime.now(UTC)
        if on_progress is not None:
            await on_progress(50)

    driver = MagicMock()
    driver.push_firmware = AsyncMock(side_effect=slow_push)

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)

    with patch.object(edge_device_service, "get_driver", return_value=driver), \
         patch.object(edge_device_service, "resolve_firmware_path", return_value=Path("x.bin")), \
         patch.object(edge_device_service, "async_session_factory", return_value=session):
        await edge_device_service.run_ota_task(task_id)

    assert task.status == EdgeOtaTaskStatus.CANCELED
    assert task.progress == 0  # 取消后进度不再回写


@pytest.mark.asyncio
async def test_run_ota_task_is_noop_for_non_pending_task() -> None:
    task_id = uuid.uuid4()
    task = SimpleNamespace(
        id=task_id, status=EdgeOtaTaskStatus.CANCELED, progress=50, log="[x] 用户取消了任务"
    )

    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(return_value=task)
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)

    with patch.object(edge_device_service, "get_driver") as get_driver, \
         patch.object(edge_device_service, "async_session_factory", return_value=session):
        await edge_device_service.run_ota_task(task_id)

    # 已取消/已结束的任务不得被后台任务重新拉起
    assert get_driver.call_count == 0
    assert db.commit.await_count == 0


@pytest.mark.asyncio
async def test_run_ota_task_fails_when_device_metadata_incomplete() -> None:
    task_id = uuid.uuid4()
    user_id = uuid.uuid4()
    device_id = uuid.uuid4()

    task = SimpleNamespace(
        id=task_id,
        user_id=user_id,
        device_id=device_id,
        firmware_id=None,
        status=EdgeOtaTaskStatus.PENDING,
        progress=0,
        log=None,
        error=None,
        started_at=None,
        finished_at=None,
    )

    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, object_id: task if object_id == task_id else None)
    db.commit = AsyncMock()

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=db)
    session.__aexit__ = AsyncMock(return_value=False)

    with patch.object(edge_device_service, "get_driver") as get_driver, \
         patch.object(edge_device_service, "async_session_factory", return_value=session):
        await edge_device_service.run_ota_task(task_id)

    assert task.status == EdgeOtaTaskStatus.FAILED
    assert get_driver.call_count == 0


# ---------------------------------------------------------------------------
# 设备建档 IP 校验
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_device_rejects_invalid_ip() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with pytest.raises(ValueError, match="非法的设备 IP"):
        await edge_device_service.create_device(
            db,
            uuid.uuid4(),
            EdgeDeviceCreate(name="测试设备", chip="esp32s3", ip_address="300.1.1.1"),
        )
    assert db.add.call_count == 0


@pytest.mark.asyncio
async def test_create_device_accepts_valid_ip() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    device = await edge_device_service.create_device(
        db,
        uuid.uuid4(),
        EdgeDeviceCreate(name="测试设备", chip="esp32s3", ip_address="192.168.1.42"),
    )

    assert device.status == EdgeDeviceStatus.UNKNOWN
    assert device.ip_address == "192.168.1.42"


# ---------------------------------------------------------------------------
# 局域网扫描
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_scan_separates_claimed_from_unclaimed() -> None:
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    claimed = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        name="已认领设备",
        ip_address="192.168.1.42",
        status=EdgeDeviceStatus.OFFLINE,
        last_online_at=None,
    )
    silent = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        name="离线设备",
        ip_address="192.168.1.99",
        status=EdgeDeviceStatus.ONLINE,
        last_online_at=None,
    )

    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [claimed, silent]
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()

    hits = [
        SimpleNamespace(ip="192.168.1.42", payload="Desk-Emoji_192.168.1.42", seen_count=2),
        SimpleNamespace(ip="192.168.1.77", payload="192.168.1.77", seen_count=1),
    ]

    with patch.object(
        edge_device_service, "list_devices", AsyncMock(return_value=[claimed, silent])
    ), patch.object(
        edge_device_service, "scan_udp_broadcast", AsyncMock(return_value=hits)
    ), patch.object(
        edge_device_service,
        "get_settings",
        return_value=SimpleNamespace(edge_udp_port=4210, edge_scan_timeout=3.0),
    ):
        result = await edge_device_service.run_scan(db, user_id)

    # 命中且已建档 -> 上线；建档但未命中 -> 离线
    assert claimed.status == EdgeDeviceStatus.ONLINE
    assert claimed.last_online_at is not None
    assert silent.status == EdgeDeviceStatus.OFFLINE

    # 未建档的 IP 进入待认领列表，已建档的不重复出现
    assert [item["ip"] for item in result["unclaimed"]] == ["192.168.1.77"]
    matched_ips = {item["ip_address"] for item in result["matched"]}
    assert matched_ips == {"192.168.1.42", "192.168.1.99"}
    assert next(item for item in result["matched"] if item["ip_address"] == "192.168.1.42")[
        "online"
    ] is True
