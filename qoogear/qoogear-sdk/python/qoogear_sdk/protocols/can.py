"""CAN/CAN-FD 通信库"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class CANMessage:
    """CAN 消息帧"""
    id: int               # CAN ID (11/29 bit)
    data: bytes           # 负载数据 (0-8 bytes CAN, 0-64 bytes CAN-FD)
    timestamp: float = 0.0
    is_extended: bool = False
    is_fd: bool = False   # CAN-FD 标志
    is_remote: bool = False

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.monotonic()


class CANInterface:
    """CAN/CAN-FD 总线接口。

    提供 CAN 2.0A/B 和 CAN-FD 协议的抽象接口。
    支持消息收发、ID过滤、波特率配置和总线诊断。

    Usage:
        can = CANInterface(channel="can0", bitrate=1000000)
        can.open()
        can.send(CANMessage(id=0x100, data=b'\x01\x02\x03'))
        msg = can.receive(timeout=1.0)
    """

    # 标准波特率
    STANDARD_BITRATES = {
        125000, 250000, 500000, 1000000,  # CAN 2.0
        2000000, 5000000, 8000000,         # CAN-FD 数据段
    }

    def __init__(self, channel: str = "can0", bitrate: int = 1000000,
                 fd_bitrate: int = 5000000, is_fd: bool = True):
        self._channel = channel
        self._bitrate = bitrate
        self._fd_bitrate = fd_bitrate
        self._is_fd = is_fd
        self._opened = False
        self._filters: List[Dict] = []  # [{id, mask, extended}]
        self._error_counters = {"tx": 0, "rx": 0}
        self._stats = {"tx_count": 0, "rx_count": 0, "errors": 0}
        self._callbacks: Dict[int, List[Callable]] = {}
        self._rx_buffer: List[CANMessage] = []

    @property
    def channel(self) -> str:
        return self._channel

    @property
    def is_open(self) -> bool:
        return self._opened

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    # ---- 生命周期 ----

    def open(self) -> bool:
        """打开 CAN 接口"""
        # 实际实现：socketcan / kvaser / peak / vector 等
        self._opened = True
        return True

    def close(self) -> None:
        """关闭 CAN 接口"""
        self._opened = False

    # ---- 消息收发 ----

    def send(self, msg: CANMessage) -> bool:
        """发送 CAN 消息"""
        if not self._opened:
            return False
        self._stats["tx_count"] += 1
        return True

    def receive(self, timeout: float = 0.0) -> Optional[CANMessage]:
        """接收 CAN 消息（阻塞/非阻塞）"""
        if not self._opened:
            return None
        if self._rx_buffer:
            msg = self._rx_buffer.pop(0)
            self._stats["rx_count"] += 1
            return msg
        return None

    def send_receive(self, msg: CANMessage, response_id: int, timeout: float = 1.0) -> Optional[CANMessage]:
        """发送并等待响应（SDO 模式）"""
        self.send(msg)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            resp = self.receive(timeout=0.01)
            if resp and resp.id == response_id:
                return resp
        return None

    # ---- 消息过滤 ----

    def set_filter(self, can_id: int, mask: int = 0x7FF, extended: bool = False) -> None:
        """设置接收过滤器"""
        self._filters.append({"id": can_id, "mask": mask, "extended": extended})

    def clear_filters(self) -> None:
        """清除所有过滤器"""
        self._filters.clear()

    def _match_filter(self, msg: CANMessage) -> bool:
        """检查消息是否匹配过滤器"""
        if not self._filters:
            return True
        for f in self._filters:
            if msg.is_extended == f["extended"] and (msg.id & f["mask"]) == (f["id"] & f["mask"]):
                return True
        return False

    # ---- 回调 ----

    def on_message(self, can_id: int, callback: Callable[[CANMessage], None]) -> None:
        """注册消息回调"""
        if can_id not in self._callbacks:
            self._callbacks[can_id] = []
        self._callbacks[can_id].append(callback)

    # ---- 协议辅助 ----

    @staticmethod
    def pack_float(value: float) -> bytes:
        """打包 float32 到 CAN 负载"""
        return struct.pack("<f", value)

    @staticmethod
    def unpack_float(data: bytes, offset: int = 0) -> float:
        """从 CAN 负载解包 float32"""
        return struct.unpack("<f", data[offset:offset + 4])[0]

    @staticmethod
    def pack_int16(value: int) -> bytes:
        """打包 int16 到 CAN 负载"""
        return struct.pack("<h", value)

    @staticmethod
    def unpack_int16(data: bytes, offset: int = 0) -> int:
        """从 CAN 负载解包 int16"""
        return struct.unpack("<h", data[offset:offset + 2])[0]

    @staticmethod
    def pack_uint16(value: int) -> bytes:
        """打包 uint16 到 CAN 负载"""
        return struct.pack("<H", value)

    @staticmethod
    def unpack_uint16(data: bytes, offset: int = 0) -> int:
        """从 CAN 负载解包 uint16"""
        return struct.unpack("<H", data[offset:offset + 2])[0]

    # ---- 诊断 ----

    def get_error_counters(self) -> dict:
        """获取错误计数器"""
        return dict(self._error_counters)

    def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {"tx_count": 0, "rx_count": 0, "errors": 0}
        self._error_counters = {"tx": 0, "rx": 0}

    def bus_off_recovery(self) -> bool:
        """总线关闭恢复"""
        if self._error_counters["tx"] > 255:
            self._error_counters["tx"] = 0
            self._error_counters["rx"] = 0
            return self.open()
        return True
