"""局域网边缘设备 UDP 广播扫描器。

设备侧协议（对齐 desk-talk V1/V3 固件）：
  固件在 conversation 主循环里每秒向 `255.255.255.255:<port>` 广播一次本机 IP。
  V3 固件 payload 是裸 IP 字符串；V1 固件是 ``Desk-Emoji_<IP>``。
  两端都不带设备名/芯片/固件版本，因此本模块只用广播做「在线判定 + 未认领 IP 发现」，
  设备元数据由用户在界面上手动维护。

参考：``desk-talk/V3/desk_talk_idf/main/wifi_manager.cpp:339-350``（send_ip_broadcast）
      ``desk-talk/V3/desk_talk_idf/main/conversation.cpp:60-69``（每秒调用一次）
"""

import asyncio
import ipaddress
import socket
import time
from typing import NamedTuple

# 2026-09-30 新增边缘设备管理模块：默认广播端口与固件 kUdpPort 保持一致
DEFAULT_BROADCAST_PORT = 4210

# 单次接收的超时。广播本身是 1Hz，取 0.5s 保证一个窗口内至少能收到一次
_RECV_TIMEOUT = 0.5

_MAX_PAYLOAD_BYTES = 512


class ScanUnavailableError(RuntimeError):
    """UDP 端口无法绑定（被其它程序占用 / 无权限）。"""


class BroadcastHit(NamedTuple):
    ip: str
    payload: str
    seen_count: int


def parse_broadcast_payload(payload: str) -> str | None:
    """从广播 payload 中提取设备 IP。

    兼容两种固件格式：裸 IP（V3）与 ``<名称>_<IP>``（V1）。
    提取不到合法 IP 时返回 None，交由调用方忽略该包。
    """
    text = payload.strip()
    if not text:
        return None

    # V3 格式：payload 整体就是一个 IP
    candidate = text.split("\n", 1)[0].strip()
    if _is_ipv4(candidate):
        return candidate

    # V1 格式：Desk-Emoji_192.168.1.42 —— 取最后一段按 IP 解析
    if "_" in candidate:
        tail = candidate.rsplit("_", 1)[-1].strip()
        if _is_ipv4(tail):
            return tail
    return None


def _is_ipv4(text: str) -> bool:
    try:
        return ipaddress.IPv4Address(text).version == 4
    except (ipaddress.AddressValueError, ValueError):
        return False


def _blocking_scan(port: int, timeout: float) -> dict[str, tuple[str, int]]:
    """阻塞式扫描，返回 ``{ip: (payload, seen_count)}``。在独立线程中执行。"""
    hits: dict[str, tuple[str, int]] = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 广播接收方需要显式允许，否则部分平台收不到 255.255.255.255 的数据报
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # 绑定任意网卡的广播端口；端口被占用时直接抛错，由上层转成 503
        sock.bind(("", port))
    except OSError as exc:
        sock.close()
        raise ScanUnavailableError(
            f"无法绑定 UDP {port} 端口：{exc}。该端口可能已被其它程序占用。"
        ) from exc

    sock.settimeout(_RECV_TIMEOUT)
    deadline = time.monotonic() + timeout
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            # 单个 recv 最多等 _RECV_TIMEOUT，避免长于外层 deadline 空转
            sock.settimeout(min(_RECV_TIMEOUT, remaining))
            try:
                data, addr = sock.recvfrom(_MAX_PAYLOAD_BYTES)
            except socket.timeout:
                continue
            except OSError:
                continue

            source_ip = addr[0]
            payload = data.decode("utf-8", errors="replace").strip()
            device_ip = parse_broadcast_payload(payload) or source_ip
            previous = hits.get(device_ip)
            seen = previous[1] + 1 if previous else 1
            hits[device_ip] = (payload, seen)
    finally:
        sock.close()

    return hits


async def scan_udp_broadcast(port: int = DEFAULT_BROADCAST_PORT, timeout: float = 3.0) -> list[BroadcastHit]:
    """在 ``timeout`` 秒窗口内收集局域网内所有广播设备。

    阻塞式 socket 操作放到线程池执行，避免占住事件循环拖慢其它请求。
    """
    if timeout <= 0:
        return []
    hits = await asyncio.to_thread(_blocking_scan, port, timeout)
    return [BroadcastHit(ip=ip, payload=payload, seen=seen) for ip, (payload, seen) in hits.items()]
