from unittest.mock import patch

import pytest

from app.services.edge_device_scanner import (
    DEFAULT_BROADCAST_PORT,
    BroadcastHit,
    ScanUnavailableError,
    _blocking_scan,
    parse_broadcast_payload,
)


def test_default_broadcast_port_matches_firmware() -> None:
    # 与固件 kUdpPort 保持一致，改任一侧都必须同步
    assert DEFAULT_BROADCAST_PORT == 4210


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("192.168.1.42", "192.168.1.42"),
        ("  192.168.1.42\n", "192.168.1.42"),
        ("Desk-Emoji_192.168.1.42", "192.168.1.42"),
        ("Desk-Emoji_10.0.0.7\n", "10.0.0.7"),
        ("random_prefix_172.16.5.3", "172.16.5.3"),
        # 无法提取 IP 的 payload 交给调用方回退用源地址
        ("Desk-Emoji", None),
        ("hello world", None),
        ("", None),
        ("999.999.999.999", None),
    ],
)
def test_parse_broadcast_payload(payload: str, expected: str | None) -> None:
    assert parse_broadcast_payload(payload) == expected


def test_broadcast_hit_fields() -> None:
    hit = BroadcastHit(ip="192.168.1.42", payload="Desk-Emoji_192.168.1.42", seen_count=3)
    assert hit.ip == "192.168.1.42"
    assert hit.seen_count == 3


def test_scan_returns_empty_on_silent_network() -> None:
    # 绑定一个几乎不可能有设备广播的端口，验证超时能正常返回而不抛错
    assert _blocking_scan(port=43999, timeout=0.2) == {}


def test_scan_raises_when_port_taken() -> None:
    import socket

    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("", 0))
    _, port = blocker.getsockname()
    try:
        with pytest.raises(ScanUnavailableError):
            _blocking_scan(port=port, timeout=0.1)
    finally:
        blocker.close()


class _FakeBroadcastSocket:
    """按脚本依次返回数据报，取尽后抛 socket.timeout 结束扫描循环。"""

    def __init__(self, script: list[tuple[bytes, tuple[str, int]]]) -> None:
        self._script = script
        self._index = 0
        self.closed = False

    def setsockopt(self, *_args) -> None:
        return None

    def bind(self, _address) -> None:
        return None

    def settimeout(self, _value: float) -> None:
        return None

    def recvfrom(self, _size):
        if self._index >= len(self._script):
            raise TimeoutError
        item = self._script[self._index]
        self._index += 1
        return item

    def close(self) -> None:
        self.closed = True


def test_scan_aggregates_repeated_broadcasts() -> None:
    """同一 IP 多次广播应累加 seen_count，而非互相覆盖。"""
    script = [
        (b"Desk-Emoji_192.168.1.42", ("192.168.1.42", 4210)),
        (b"192.168.1.99", ("192.168.1.99", 4210)),
        (b"Desk-Emoji_192.168.1.42", ("192.168.1.42", 4210)),
    ]
    fake = _FakeBroadcastSocket(script)
    with patch("socket.socket", return_value=fake):
        hits = _blocking_scan(port=4210, timeout=0.2)

    assert hits["192.168.1.42"] == ("Desk-Emoji_192.168.1.42", 2)
    assert hits["192.168.1.99"] == ("192.168.1.99", 1)
    assert fake.closed
