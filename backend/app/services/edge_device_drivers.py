"""边缘设备通信驱动抽象。

Web 管理端与设备之间走 HTTP，但固件侧的管理接口尚未实现
（desk-talk V3 目前只有 AP 配网期的 ``/scan-wifi`` / ``/save-wifi``，无 OTA、无运行时配置接口）。
因此这里定义一层 ``DeviceDriver`` 抽象：本期默认实现走 HTTP 约定协议，
设备不支持时返回结构化错误码而不是超时白屏；另提供 Mock 驱动，在没有真机时
也能完整演练「上传固件 → 推送到设备 → 分片进度 → 完成」的链路。

**设备侧 HTTP 管理接口约定**（待固件补齐，实现时照此对接即可，上层无需改动）::

    GET  http://{ip}/api/info
         -> 200 {"name": "...", "chip": "esp32s3", "version": "3.0.1", "mac": "AA:.."}

    GET  http://{ip}/api/ota/status
         -> 200 {"state": "idle|writing|done|error", "progress": 0-100, "message": "..."}

    POST http://{ip}/api/ota                 multipart/form-data, 字段名 firmware
         <- 202 {"status": "accepted"}
         -> 404/501 表示设备固件不支持 OTA

    POST http://{ip}/api/wifi                {"ssid": "...", "password": "..."}
         <- 200 {"status": "saved"}

    POST http://{ip}/api/config              {"llm": {...}, "prompt": "..."}
         <- 200 {"status": "saved"}

**安全约束**：所有驱动的目标 IP 都来自用户在界面上填的 ``ip_address``，
属于不可信输入。统一由 :func:`assert_lan_address` 收敛，只放行私网/回环地址，
挡住 ``169.254.169.254``（云元数据）之类把本模块当成 SSRF 跳板的用法。
"""

import asyncio
import ipaddress
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Awaitable, Callable

import httpx

from app.core.config import get_settings

__all__ = [
    "DeviceCommandError",
    "DeviceDriver",
    "HttpDeviceDriver",
    "MockDeviceDriver",
    "get_driver",
    "assert_lan_address",
]

# 进度回调：收到 0-100 的整数进度时调用
ProgressCallback = Callable[[int], Awaitable[None]]


class DeviceCommandError(RuntimeError):
    """设备通信失败。code 为稳定的错误码，前端据此给出中文提示。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def assert_lan_address(ip: str) -> str:
    """校验目标地址是私网或回环地址，否则拒绝连接（SSRF 防护）。"""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError as exc:
        raise DeviceCommandError("invalid-ip", f"非法的设备 IP：{ip}") from exc

    # Python 3.12 起 is_private 的语义收窄，link-local（169.254/16）与
    # unspecified（0.0.0.0）都被算作 private。只靠 is_private 会漏掉云元数据
    # 地址 169.254.169.254，所以这里显式把特殊段再排除一遍。
    if (
        not (address.is_private or address.is_loopback)
        or address.is_link_local
        or address.is_unspecified
        or address.is_multicast
        or address.is_reserved
    ):
        raise DeviceCommandError(
            "ip-not-allowed", f"设备 IP {ip} 不在局域网范围内，已拒绝连接"
        )
    return ip


class DeviceDriver(ABC):
    """设备通信驱动接口。固件协议演进时只需新增实现，不改上层业务。"""

    name: str = "abstract"

    @abstractmethod
    async def push_firmware(
        self,
        ip: str,
        firmware_path: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        """把本地固件文件推送到设备并触发升级。"""

    @abstractmethod
    async def push_wifi(self, ip: str, ssid: str, password: str) -> None:
        """下发 WiFi 凭证。"""

    @abstractmethod
    async def push_llm_config(self, ip: str, config: dict) -> None:
        """下发 LLM API 配置（base_url / model / api_key / temperature）。"""

    @abstractmethod
    async def push_prompt(self, ip: str, prompt: str) -> None:
        """下发默认系统 Prompt。"""


class HttpDeviceDriver(DeviceDriver):
    """默认驱动：按模块 docstring 的约定协议访问设备 HTTP 管理接口。"""

    name = "http"

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    async def push_firmware(
        self,
        ip: str,
        firmware_path: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        assert_lan_address(ip)
        path = Path(firmware_path)
        if not path.is_file():
            raise DeviceCommandError("firmware-missing", f"固件文件不存在：{firmware_path}")

        if on_progress is not None:
            await on_progress(0)

        # 固件比普通 API 请求大得多，读取阶段单独放宽超时，避免大文件传到一半被切断
        timeout = httpx.Timeout(self._timeout, read=max(self._timeout, 120.0))
        try:
            with path.open("rb") as handle:
                files = {"firmware": (path.name, handle, "application/octet-stream")}
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(f"http://{ip}/api/ota", files=files)
        except httpx.TimeoutException as exc:
            raise DeviceCommandError("device-timeout", f"设备 {ip} 响应超时") from exc
        except httpx.HTTPError as exc:
            raise DeviceCommandError("device-unreachable", f"无法连接设备 {ip}：{exc}") from exc

        if response.status_code in (404, 501):
            raise DeviceCommandError(
                "device-ota-unsupported",
                "设备固件暂不支持 OTA 升级，请改用有线烧录，或先升级设备端固件",
            )
        if response.status_code >= 400:
            raise DeviceCommandError(
                "device-rejected",
                f"设备拒绝 OTA 请求（HTTP {response.status_code}）：{response.text[:200]}",
            )

        if on_progress is not None:
            await on_progress(100)

    async def push_wifi(self, ip: str, ssid: str, password: str) -> None:
        await self._post_json(ip, "/api/wifi", {"ssid": ssid, "password": password})

    async def push_llm_config(self, ip: str, config: dict) -> None:
        await self._post_json(ip, "/api/config", {"llm": config})

    async def push_prompt(self, ip: str, prompt: str) -> None:
        await self._post_json(ip, "/api/config", {"prompt": prompt})

    async def _post_json(self, ip: str, path: str, payload: dict) -> dict:
        assert_lan_address(ip)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"http://{ip}{path}", json=payload)
        except httpx.TimeoutException as exc:
            raise DeviceCommandError("device-timeout", f"设备 {ip} 响应超时") from exc
        except httpx.HTTPError as exc:
            raise DeviceCommandError("device-unreachable", f"无法连接设备 {ip}：{exc}") from exc

        if response.status_code in (404, 501):
            raise DeviceCommandError(
                "device-api-unsupported",
                "设备固件暂不支持远程配置下发，请在 AP 配网模式下手动设置",
            )
        if response.status_code >= 400:
            raise DeviceCommandError(
                "device-rejected",
                f"设备拒绝请求（HTTP {response.status_code}）：{response.text[:200]}",
            )
        try:
            return response.json()
        except ValueError:
            return {}


class MockDeviceDriver(DeviceDriver):
    """无真机时演练全流程的模拟驱动。

    按固定分片推进进度，每片之间让出事件循环，使后台任务能持续把进度写库、
    前端轮询能看到进度平滑增长。
    """

    name = "mock"
    _CHUNKS = 8

    async def push_firmware(
        self,
        ip: str,
        firmware_path: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        if on_progress is not None:
            await on_progress(0)
        for index in range(1, self._CHUNKS + 1):
            await asyncio.sleep(0.2)
            if on_progress is not None:
                await on_progress(int(index * 100 / self._CHUNKS))

    async def push_wifi(self, ip: str, ssid: str, password: str) -> None:
        await asyncio.sleep(0.05)

    async def push_llm_config(self, ip: str, config: dict) -> None:
        await asyncio.sleep(0.05)

    async def push_prompt(self, ip: str, prompt: str) -> None:
        await asyncio.sleep(0.05)


_DRIVERS: dict[str, type[DeviceDriver]] = {
    HttpDeviceDriver.name: HttpDeviceDriver,
    MockDeviceDriver.name: MockDeviceDriver,
}


def get_driver() -> DeviceDriver:
    """按配置返回设备驱动实例。配置了未知驱动名时回退到 HTTP 驱动。"""
    settings = get_settings()
    driver_cls = _DRIVERS.get(settings.edge_device_driver, HttpDeviceDriver)
    return driver_cls()
