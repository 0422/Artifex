from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from app.services.edge_device_drivers import (
    DeviceCommandError,
    HttpDeviceDriver,
    MockDeviceDriver,
    assert_lan_address,
    get_driver,
)


# ---------------------------------------------------------------------------
# SSRF 防护：设备 IP 来自用户输入，必须挡在连接之前
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ip", ["192.168.1.42", "10.0.0.5", "172.16.8.9", "127.0.0.1"])
def test_assert_lan_address_allows_private(ip: str) -> None:
    assert assert_lan_address(ip) == ip


@pytest.mark.parametrize(
    "ip",
    [
        "8.8.8.8",  # 公网 DNS
        "169.254.169.254",  # 云元数据地址，链路本地
        "1.1.1.1",
        "224.0.0.1",  # 组播
        "0.0.0.0",
    ],
)
def test_assert_lan_address_rejects_non_private(ip: str) -> None:
    with pytest.raises(DeviceCommandError) as exc_info:
        assert_lan_address(ip)
    assert exc_info.value.code == "ip-not-allowed"


def test_assert_lan_address_rejects_garbage() -> None:
    with pytest.raises(DeviceCommandError) as exc_info:
        assert_lan_address("not-an-ip")
    assert exc_info.value.code == "invalid-ip"


# ---------------------------------------------------------------------------
# 驱动选择
# ---------------------------------------------------------------------------


def test_get_driver_returns_mock_when_configured() -> None:
    with patch("app.services.edge_device_drivers.get_settings") as settings:
        settings.return_value = SimpleNamespace(edge_device_driver="mock")
        assert isinstance(get_driver(), MockDeviceDriver)


def test_get_driver_falls_back_to_http_on_unknown_name() -> None:
    # 配置写错驱动名时回退到 HTTP 驱动，而不是启动即崩
    with patch("app.services.edge_device_drivers.get_settings") as settings:
        settings.return_value = SimpleNamespace(edge_device_driver="typo-driver")
        assert isinstance(get_driver(), HttpDeviceDriver)


# ---------------------------------------------------------------------------
# Mock 驱动：无真机时演练全流程
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_driver_reports_monotonic_progress() -> None:
    driver = MockDeviceDriver()
    progresses: list[int] = []

    async def on_progress(value: int) -> None:
        progresses.append(value)

    await driver.push_firmware("192.168.1.42", "/tmp/fake.bin", on_progress=on_progress)

    assert progresses[0] == 0
    assert progresses[-1] == 100
    assert progresses == sorted(progresses)


@pytest.mark.asyncio
async def test_mock_driver_config_calls_succeed_without_device() -> None:
    driver = MockDeviceDriver()
    await driver.push_wifi("192.168.1.42", "MySSID", "secret")
    await driver.push_llm_config("192.168.1.42", {"model": "gpt-4o"})
    await driver.push_prompt("192.168.1.42", "你是学习助手")


# ---------------------------------------------------------------------------
# HTTP 驱动：设备侧接口的各类响应翻译成稳定错误码
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def _install_client(monkeypatch, behaviour) -> list[tuple[str, bool]]:
    """把 httpx.AsyncClient 换成脚本化替身，返回 [(url, 是否发送 json)] 调用记录。"""
    recorded: list[tuple[str, bool]] = []

    class FakeAsyncClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> bool:
            return False

        async def post(self, url: str, **kwargs):
            recorded.append((url, "json" in kwargs))
            outcome = behaviour(url)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return recorded


@pytest.fixture
def firmware_file(tmp_path: Path) -> Path:
    path = tmp_path / "firmware.bin"
    path.write_bytes(b"\x00" * 64)
    return path


@pytest.mark.asyncio
async def test_http_driver_reports_ota_unsupported_on_404(monkeypatch, firmware_file: Path) -> None:
    _install_client(monkeypatch, lambda url: _FakeResponse(404))

    with pytest.raises(DeviceCommandError) as exc_info:
        await HttpDeviceDriver().push_firmware("192.168.1.42", str(firmware_file))

    assert exc_info.value.code == "device-ota-unsupported"


@pytest.mark.asyncio
async def test_http_driver_reports_rejection_on_500(monkeypatch, firmware_file: Path) -> None:
    _install_client(monkeypatch, lambda url: _FakeResponse(500, text="flash write failed"))

    with pytest.raises(DeviceCommandError) as exc_info:
        await HttpDeviceDriver().push_firmware("192.168.1.42", str(firmware_file))

    assert exc_info.value.code == "device-rejected"
    assert "flash write failed" in exc_info.value.message


@pytest.mark.asyncio
async def test_http_driver_reports_success_and_progress(monkeypatch, firmware_file: Path) -> None:
    _install_client(monkeypatch, lambda url: _FakeResponse(202, {"status": "accepted"}))
    progresses: list[int] = []

    async def on_progress(value: int) -> None:
        progresses.append(value)

    await HttpDeviceDriver().push_firmware(
        "192.168.1.42", str(firmware_file), on_progress=on_progress
    )

    assert progresses == [0, 100]


@pytest.mark.asyncio
async def test_http_driver_reports_unreachable(monkeypatch, firmware_file: Path) -> None:
    _install_client(monkeypatch, lambda url: httpx.ConnectError("connection refused"))

    with pytest.raises(DeviceCommandError) as exc_info:
        await HttpDeviceDriver().push_firmware("192.168.1.42", str(firmware_file))

    assert exc_info.value.code == "device-unreachable"


@pytest.mark.asyncio
async def test_http_driver_reports_missing_firmware_file() -> None:
    with pytest.raises(DeviceCommandError) as exc_info:
        await HttpDeviceDriver().push_firmware("192.168.1.42", "C:/nope/missing.bin")

    assert exc_info.value.code == "firmware-missing"


@pytest.mark.asyncio
async def test_http_driver_refuses_public_ip_before_connecting(monkeypatch, firmware_file: Path) -> None:
    recorded = _install_client(monkeypatch, lambda url: _FakeResponse(202))

    with pytest.raises(DeviceCommandError) as exc_info:
        await HttpDeviceDriver().push_firmware("169.254.169.254", str(firmware_file))

    assert exc_info.value.code == "ip-not-allowed"
    assert recorded == []  # 一条请求都没发出去


@pytest.mark.asyncio
async def test_http_driver_config_unsupported_on_404(monkeypatch) -> None:
    _install_client(monkeypatch, lambda url: _FakeResponse(404))

    with pytest.raises(DeviceCommandError) as exc_info:
        await HttpDeviceDriver().push_wifi("192.168.1.42", "SSID", "pwd")

    assert exc_info.value.code == "device-api-unsupported"


@pytest.mark.asyncio
async def test_http_driver_push_prompt_sends_json(monkeypatch) -> None:
    recorded = _install_client(monkeypatch, lambda url: _FakeResponse(200, {"status": "saved"}))

    await HttpDeviceDriver().push_prompt("192.168.1.42", "你是学习助手")

    url, used_json = recorded[0]
    assert url == "http://192.168.1.42/api/config"
    assert used_json
