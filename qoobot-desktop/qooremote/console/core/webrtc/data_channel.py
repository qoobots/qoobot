"""DataChannel 管理 — WebRTC 数据通道的创建/协议/多通道管理

在 WebRTC 上建立多个逻辑数据通道：
- control: 遥操作控制指令
- state: 机器人状态上报
- alert: 告警通知
- file: 文件传输

对应功能 CON-02（WebRTC 数据通道）。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 通道定义
# ------------------------------------------------------------------

class ChannelRole(Enum):
    """通道角色"""
    CONTROL = "control"      # 遥操作控制指令（高优先、低延迟）
    STATE = "state"          # 机器人状态上报（中优先、可靠）
    ALERT = "alert"          # 告警通知（高优先、可靠）
    FILE = "file"            # 文件传输（低优先、可靠）
    CUSTOM = "custom"        # 自定义通道


@dataclass
class ChannelConfig:
    """DataChannel 配置"""
    role: ChannelRole
    label: str
    ordered: bool = True
    max_retransmits: int = -1       # -1 表示无限重传（可靠）
    max_packet_life_time_ms: int = 5000
    priority: int = 0               # 0=最高, 1=高, 2=中, 3=低

    @classmethod
    def control(cls) -> "ChannelConfig":
        return cls(ChannelRole.CONTROL, "control", ordered=True,
                   max_retransmits=0, priority=0)  # 不重传：低延迟优先

    @classmethod
    def state(cls) -> "ChannelConfig":
        return cls(ChannelRole.STATE, "state", ordered=True,
                   max_retransmits=-1, priority=1)

    @classmethod
    def alert(cls) -> "ChannelConfig":
        return cls(ChannelRole.ALERT, "alert", ordered=True,
                   max_retransmits=-1, priority=0)

    @classmethod
    def file_transfer(cls) -> "ChannelConfig":
        return cls(ChannelRole.FILE, "file", ordered=True,
                   max_retransmits=-1, priority=2)


# ------------------------------------------------------------------
# 消息封装
# ------------------------------------------------------------------

@dataclass
class ChannelMessage:
    """DataChannel 消息"""
    type: str                       # 消息类型
    payload: Any = None             # 消息负载
    timestamp: float = field(default_factory=time.time)
    seq: int = 0                    # 序列号

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "payload": self.payload,
            "ts": self.timestamp,
            "seq": self.seq,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> "ChannelMessage":
        obj = json.loads(data)
        return cls(
            type=obj.get("type", ""),
            payload=obj.get("payload"),
            timestamp=obj.get("ts", 0),
            seq=obj.get("seq", 0),
        )


# ------------------------------------------------------------------
# 数据通道管理器
# ------------------------------------------------------------------

class DataChannelManager:
    """WebRTC DataChannel 多通道管理器

    管理 control/state/alert/file 四个逻辑通道。
    提供统一的收发接口和统计。
    """

    def __init__(self) -> None:
        self._channels: dict[str, ManagedChannel] = {}
        self._lock = Lock()
        self._seq_counter = 0
        self._is_open = False

        # 默认通道配置
        self._default_configs: list[ChannelConfig] = [
            ChannelConfig.control(),
            ChannelConfig.state(),
            ChannelConfig.alert(),
            ChannelConfig.file_transfer(),
        ]

        # 回调
        self.on_control_message: Optional[Callable[[ChannelMessage], None]] = None
        self.on_state_message: Optional[Callable[[ChannelMessage], None]] = None
        self.on_alert_message: Optional[Callable[[ChannelMessage], None]] = None
        self.on_file_data: Optional[Callable[[bytes, str], None]] = None  # (data, filename)

    # ---- 生命周期 ----

    def create_all(self) -> list[ManagedChannel]:
        """创建所有默认通道"""
        channels = []
        for cfg in self._default_configs:
            ch = self.create_channel(cfg)
            channels.append(ch)
        return channels

    def create_channel(self, config: ChannelConfig) -> "ManagedChannel":
        """创建单个通道"""
        with self._lock:
            ch = ManagedChannel(config, self)
            self._channels[config.label] = ch
            logger.info("DataChannel created: %s (role=%s)", config.label, config.role.value)
            return ch

    def open_all(self) -> None:
        """打开所有通道"""
        self._is_open = True
        for ch in self._channels.values():
            ch.open()

    def close_all(self) -> None:
        """关闭所有通道"""
        self._is_open = False
        for ch in self._channels.values():
            ch.close()

    # ---- 获取通道 ----

    def get_channel(self, role: ChannelRole) -> Optional["ManagedChannel"]:
        """按角色获取通道"""
        for ch in self._channels.values():
            if ch.config.role == role:
                return ch
        return None

    def get_control(self) -> Optional["ManagedChannel"]:
        return self.get_channel(ChannelRole.CONTROL)

    def get_state(self) -> Optional["ManagedChannel"]:
        return self.get_channel(ChannelRole.STATE)

    def get_alert(self) -> Optional["ManagedChannel"]:
        return self.get_channel(ChannelRole.ALERT)

    def get_file(self) -> Optional["ManagedChannel"]:
        return self.get_channel(ChannelRole.FILE)

    # ---- 便捷发送 ----

    def send_control(self, msg_type: str, payload: Any = None) -> bool:
        """发送控制指令"""
        ch = self.get_control()
        if ch:
            ch.send(ChannelMessage(type=msg_type, payload=payload, seq=self._next_seq()))
            return True
        return False

    def send_state(self, msg_type: str, payload: Any = None) -> bool:
        """发送状态数据"""
        ch = self.get_state()
        if ch:
            ch.send(ChannelMessage(type=msg_type, payload=payload, seq=self._next_seq()))
            return True
        return False

    def send_alert(self, msg_type: str, payload: Any = None) -> bool:
        """发送告警"""
        ch = self.get_alert()
        if ch:
            ch.send(ChannelMessage(type=msg_type, payload=payload, seq=self._next_seq()))
            return True
        return False

    def send_file_data(self, data: bytes, filename: str = "") -> bool:
        """发送文件数据"""
        ch = self.get_file()
        if ch:
            msg = ChannelMessage(
                type="file_chunk",
                payload={
                    "filename": filename,
                    "data": data.hex() if len(data) < 65536 else f"<{len(data)} bytes>",
                    "size": len(data),
                },
                seq=self._next_seq(),
            )
            ch.send(msg)
            return True
        return False

    # ---- 消息路由 ----

    def _route_message(self, role: ChannelRole, message: ChannelMessage) -> None:
        """将消息路由到对应的回调"""
        if role == ChannelRole.CONTROL and self.on_control_message:
            self.on_control_message(message)
        elif role == ChannelRole.STATE and self.on_state_message:
            self.on_state_message(message)
        elif role == ChannelRole.ALERT and self.on_alert_message:
            self.on_alert_message(message)
        elif role == ChannelRole.FILE and self.on_file_data:
            if isinstance(message.payload, dict):
                data_hex = message.payload.get("data", "")
                filename = message.payload.get("filename", "")
                from codecs import decode
                try:
                    data = decode(data_hex, "hex") if isinstance(data_hex, str) and len(data_hex) < 65536 else b""
                except Exception:
                    data = b""
                self.on_file_data(data, filename)

    def _next_seq(self) -> int:
        self._seq_counter += 1
        return self._seq_counter

    # ---- 统计 ----

    def get_stats(self) -> dict:
        return {
            "is_open": self._is_open,
            "channel_count": len(self._channels),
            "channels": {
                label: ch.get_stats()
                for label, ch in self._channels.items()
            },
        }


class ManagedChannel:
    """被 DataChannelManager 管理的单个通道"""

    def __init__(self, config: ChannelConfig, manager: DataChannelManager) -> None:
        self.config = config
        self._manager = manager
        self._open = False
        self._send_count = 0
        self._recv_count = 0
        self._bytes_sent = 0
        self._bytes_received = 0

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        self._open = True

    def send(self, message: ChannelMessage) -> None:
        if not self._open:
            return
        self._send_count += 1
        data = message.to_json()
        self._bytes_sent += len(data)

    def receive(self, raw_data: bytes) -> None:
        try:
            message = ChannelMessage.from_json(raw_data.decode("utf-8"))
            self._recv_count += 1
            self._bytes_received += len(raw_data)
            self._manager._route_message(self.config.role, message)
        except Exception as exc:
            logger.warning("DataChannel '%s' receive error: %s", self.config.label, exc)

    def close(self) -> None:
        self._open = False

    def get_stats(self) -> dict:
        return {
            "label": self.config.label,
            "role": self.config.role.value,
            "open": self._open,
            "sent_count": self._send_count,
            "recv_count": self._recv_count,
            "bytes_sent": self._bytes_sent,
            "bytes_received": self._bytes_received,
        }
