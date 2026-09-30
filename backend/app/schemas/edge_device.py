import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EdgeDeviceStatus, EdgeOtaTaskStatus

__all__ = [
    "LlmConfig",
    "PromptConfig",
    "EdgeDeviceCreate",
    "EdgeDeviceUpdate",
    "EdgeDeviceRead",
    "EdgeWifiInput",
    "EdgePromptInput",
    "DiscoveredDevice",
    "DeviceScanState",
    "ScanResult",
    "EdgeFirmwareRead",
    "EdgeOtaTaskCreate",
    "EdgeOtaTaskRead",
]

# api_key 脱敏后统一返回这个前缀，末 4 位保留原文，方便用户辨认是哪把 key。
# 提交时若值仍以该前缀开头，service 层会判定为「未修改」而不回写。
MASK_PREFIX = "****"


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return MASK_PREFIX
    return f"{MASK_PREFIX}{value[-4:]}"


def is_masked(value: str | None) -> bool:
    """判断提交上来的 api_key 是否只是脱敏回显，而非新的真实 key。"""
    return value is None or not value.strip() or value.startswith(MASK_PREFIX)


class LlmConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    api_key: str | None = None
    base_url: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=100)
    temperature: float | None = Field(default=None, ge=0, le=2)


class PromptConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    system_prompt: str | None = Field(default=None, max_length=8000)


class EdgeDeviceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    chip: str = Field(min_length=1, max_length=50)
    ip_address: str | None = Field(default=None, max_length=45)
    mac_address: str | None = Field(default=None, max_length=17)
    firmware_version: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)


class EdgeDeviceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    chip: str | None = Field(default=None, min_length=1, max_length=50)
    ip_address: str | None = Field(default=None, max_length=45)
    mac_address: str | None = Field(default=None, max_length=17)
    firmware_version: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)


class EdgeDeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    chip: str
    ip_address: str | None
    mac_address: str | None
    firmware_version: str | None
    status: EdgeDeviceStatus
    last_online_at: datetime | None
    wifi_ssid: str | None
    llm_config: LlmConfig | None
    prompt_config: PromptConfig | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("llm_config", mode="before")
    @classmethod
    def _mask_llm_api_key(cls, value: object) -> object:
        # 2026-09-30 边缘设备管理模块：api_key 落库为明文以便下发，但任何读取路径
        # 都不得回传明文，只留末 4 位供辨认。更新时靠 is_masked() 识别「未修改」。
        if not isinstance(value, dict):
            return value
        masked = dict(value)
        masked["api_key"] = _mask_secret(masked.get("api_key"))
        return masked


class EdgeWifiInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ssid: str = Field(min_length=1, max_length=100)
    password: str = Field(default="", max_length=100)


class EdgePromptInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    system_prompt: str = Field(min_length=1, max_length=8000)


class DiscoveredDevice(BaseModel):
    """一次 UDP 扫描命中的设备广播。"""

    ip: str
    # 固件广播的原始 payload，透传给前端便于人工辨认设备
    payload: str
    seen_count: int = Field(default=1, description="扫描窗口内收到该 IP 的广播次数")


class DeviceScanState(BaseModel):
    """已建档设备在本次扫描中的在线情况。"""

    device_id: uuid.UUID
    name: str
    ip_address: str | None
    online: bool
    payload: str | None = None


class ScanResult(BaseModel):
    scanned_at: datetime
    duration_ms: int
    port: int
    unclaimed: list[DiscoveredDevice]
    matched: list[DeviceScanState]


class EdgeFirmwareRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    version: str
    chip: str
    size_bytes: int
    sha256: str
    notes: str | None
    created_at: datetime


class EdgeOtaTaskCreate(BaseModel):
    firmware_id: uuid.UUID


class EdgeOtaTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    firmware_id: uuid.UUID | None
    status: EdgeOtaTaskStatus
    progress: int
    error: str | None
    log: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    firmware: EdgeFirmwareRead | None = None
