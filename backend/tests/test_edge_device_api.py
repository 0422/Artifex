import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.edge_device import router
from app.core.database import get_db
from app.models.enums import EdgeDeviceStatus, EdgeOtaTaskStatus


@pytest.fixture
def current_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def client(current_user: SimpleNamespace) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return TestClient(app)


def make_device(user_id: uuid.UUID, **overrides) -> SimpleNamespace:
    now = datetime.now(UTC)
    fields = dict(
        id=uuid.uuid4(),
        user_id=user_id,
        name="书桌助手",
        chip="esp32s3",
        ip_address="192.168.1.42",
        mac_address=None,
        firmware_version="3.0.1",
        status=EdgeDeviceStatus.ONLINE,
        last_online_at=now,
        wifi_ssid="HomeNet",
        # 落库是明文，响应里必须被脱敏
        llm_config={"api_key": "sk-real-secret-abcd", "model": "gpt-4o"},
        prompt_config={"system_prompt": "你是学习助手"},
        notes=None,
        created_at=now,
        updated_at=now,
        ota_tasks=[],
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_list_devices_masks_api_key(client: TestClient, current_user: SimpleNamespace) -> None:
    device = make_device(current_user.id)
    with patch(
        "app.api.v1.edge_device.edge_device_service.list_devices",
        AsyncMock(return_value=[device]),
    ):
        response = client.get("/api/v1/edge-devices")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["llm_config"]["api_key"] == "****abcd"
    assert "sk-real-secret" not in str(body)


def test_scan_returns_scan_result(
    client: TestClient, current_user: SimpleNamespace
) -> None:
    scan_payload = {
        "scanned_at": datetime.now(UTC),
        "duration_ms": 3000,
        "port": 4210,
        "unclaimed": [{"ip": "192.168.1.77", "payload": "192.168.1.77", "seen_count": 1}],
        "matched": [
            {
                "device_id": uuid.uuid4(),
                "name": "书桌助手",
                "ip_address": "192.168.1.42",
                "online": True,
                "payload": "Desk-Emoji_192.168.1.42",
            }
        ],
    }
    with patch(
        "app.api.v1.edge_device.edge_device_service.run_scan",
        AsyncMock(return_value=scan_payload),
    ) as run_scan:
        response = client.post("/api/v1/edge-devices/scan")

    assert response.status_code == 200
    assert response.json()["unclaimed"][0]["ip"] == "192.168.1.77"
    assert run_scan.await_args.args[1] == current_user.id


def test_scan_reports_unavailable_port(client: TestClient) -> None:
    from app.services.edge_device_scanner import ScanUnavailableError

    with patch(
        "app.api.v1.edge_device.edge_device_service.run_scan",
        AsyncMock(side_effect=ScanUnavailableError("无法绑定 UDP 4210")),
    ):
        response = client.post("/api/v1/edge-devices/scan")

    # 端口绑定失败属于服务端环境问题，不应被吞成 200
    assert response.status_code == 503


def test_create_device_validates_ip(client: TestClient) -> None:
    with patch(
        "app.api.v1.edge_device.edge_device_service.create_device",
        AsyncMock(side_effect=ValueError("非法的设备 IP：300.1.1.1")),
    ):
        response = client.post(
            "/api/v1/edge-devices",
            json={"name": "测试设备", "chip": "esp32s3", "ip_address": "300.1.1.1"},
        )

    assert response.status_code == 400


def test_create_device_returns_created(client: TestClient, current_user: SimpleNamespace) -> None:
    device = make_device(current_user.id)
    with patch(
        "app.api.v1.edge_device.edge_device_service.create_device",
        AsyncMock(return_value=device),
    ):
        response = client.post(
            "/api/v1/edge-devices",
            json={"name": "书桌助手", "chip": "esp32s3", "ip_address": "192.168.1.42"},
        )

    assert response.status_code == 201
    assert response.json()["name"] == "书桌助手"


def test_get_device_returns_404_for_other_users_device(client: TestClient) -> None:
    from app.services.edge_device_service import DeviceNotFoundError

    with patch(
        "app.api.v1.edge_device.edge_device_service.get_device",
        AsyncMock(side_effect=DeviceNotFoundError("设备不存在")),
    ):
        response = client.get(f"/api/v1/edge-devices/{uuid.uuid4()}")

    assert response.status_code == 404


def test_push_wifi_returns_502_when_device_rejects(client: TestClient) -> None:
    from app.services.edge_device_drivers import DeviceCommandError

    device = make_device(uuid.uuid4())
    with patch(
        "app.api.v1.edge_device.edge_device_service.push_wifi",
        AsyncMock(
            side_effect=DeviceCommandError("device-api-unsupported", "设备固件暂不支持远程配置下发")
        ),
    ):
        response = client.put(
            f"/api/v1/edge-devices/{device.id}/wifi",
            json={"ssid": "NewNet", "password": "pw"},
        )

    assert response.status_code == 502
    assert response.json()["detail"].startswith("device-api-unsupported:")


def test_push_wifi_success_mirrors_ssid(client: TestClient) -> None:
    device = make_device(uuid.uuid4(), wifi_ssid="NewNet")
    with patch(
        "app.api.v1.edge_device.edge_device_service.push_wifi",
        AsyncMock(return_value=device),
    ):
        response = client.put(
            f"/api/v1/edge-devices/{device.id}/wifi",
            json={"ssid": "NewNet", "password": "pw"},
        )

    assert response.status_code == 200
    assert response.json()["wifi_ssid"] == "NewNet"


def test_create_ota_task_starts_background_job(client: TestClient, current_user: SimpleNamespace) -> None:
    device_id = uuid.uuid4()
    firmware_id = uuid.uuid4()
    task = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=current_user.id,
        device_id=device_id,
        firmware_id=firmware_id,
        status=EdgeOtaTaskStatus.PENDING,
        progress=0,
        error=None,
        log=None,
        started_at=None,
        finished_at=None,
        created_at=datetime.now(UTC),
        firmware=None,
    )

    with patch(
        "app.api.v1.edge_device.edge_device_service.create_ota_task",
        AsyncMock(return_value=task),
    ) as create_task, patch(
        "app.api.v1.edge_device.BackgroundTasks.add_task"
    ) as add_task:
        response = client.post(
            f"/api/v1/edge-devices/{device_id}/ota-tasks",
            json={"firmware_id": str(firmware_id)},
        )

    assert response.status_code == 202
    assert create_task.await_count == 1
    assert add_task.call_count == 1


def test_get_ota_task_returns_progress(client: TestClient) -> None:
    task = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        firmware_id=None,
        status=EdgeOtaTaskStatus.RUNNING,
        progress=50,
        error=None,
        log="[12:00:00] 开始推送",
        started_at=datetime.now(UTC),
        finished_at=None,
        created_at=datetime.now(UTC),
        firmware=None,
    )
    with patch(
        "app.api.v1.edge_device.edge_device_service.get_ota_task",
        AsyncMock(return_value=task),
    ):
        response = client.get(f"/api/v1/edge-devices/ota-tasks/{task.id}")

    assert response.status_code == 200
    assert response.json()["progress"] == 50


def test_default_prompt_endpoint_is_reachable(client: TestClient) -> None:
    """/default-prompt 必须不被 /{device_id} 抢匹配，否则会因 UUID 解析失败返回 422。"""
    response = client.get("/api/v1/edge-devices/default-prompt")

    assert response.status_code == 200
    assert "学习助手" in response.json()["system_prompt"]
