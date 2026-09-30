import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import EdgeDeviceStatus, EdgeOtaTaskStatus

if TYPE_CHECKING:
    from app.models.user import User

__all__ = ["EdgeDevice", "EdgeFirmware", "EdgeOtaTask"]


# 2026-09-30 新增边缘设备管理模块：设备档案 / 固件仓库 / OTA 任务三张表。
# 设备元数据（名称、芯片、固件版本）由用户手动维护，局域网 UDP 广播只用于
# 把 ip_address 与档案对应上、判定在线状态，不承载设备元数据。
class EdgeDevice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "edge_devices"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # esp32s3 / rk3576 / esp32 / esp32c3 ...
    chip: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    # online / offline / unknown
    status: Mapped[str] = mapped_column(
        String(20), default=EdgeDeviceStatus.UNKNOWN, nullable=False, index=True
    )
    last_online_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 配网/API 配置镜像。llm_config 内可能含 api_key，读取层统一脱敏，不回传明文。
    wifi_ssid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    prompt_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    ota_tasks: Mapped[list["EdgeOtaTask"]] = relationship(
        back_populates="device", cascade="all, delete-orphan", order_by="EdgeOtaTask.created_at"
    )


# 2026-09-30 新增边缘设备管理模块：本地固件仓库。二进制落盘在 backend/firmware/，
# 表里只存元数据与 sha256，推送到设备前先校验完整性。
class EdgeFirmware(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "edge_firmware"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    chip: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # 相对 backend/ 的存储路径，如 firmware/<uuid>.bin
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# 2026-09-30 新增边缘设备管理模块：OTA 任务。进度与日志由后台任务持续回写，
# 前端轮询任务详情即可看到分片进度；设备侧无 OTA 接口时以失败码收尾。
class EdgeOtaTask(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "edge_ota_tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    firmware_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("edge_firmware.id", ondelete="SET NULL"),
        nullable=True,
    )
    # pending / running / success / failed / canceled
    status: Mapped[str] = mapped_column(
        String(20), default=EdgeOtaTaskStatus.PENDING, nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped["EdgeDevice"] = relationship(back_populates="ota_tasks")
    firmware: Mapped["EdgeFirmware | None"] = relationship()
