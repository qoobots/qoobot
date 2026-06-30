"""信令消息模型 — WebSocket 通信协议消息定义"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """信令消息类型"""
    # 连接管理
    AUTH = "auth"
    AUTH_RESPONSE = "auth_response"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"

    # 机器人管理
    LIST_ROBOTS = "list_robots"
    LIST_ROBOTS_RESPONSE = "list_robots_response"
    SELECT_ROBOT = "select_robot"
    SELECT_ROBOT_RESPONSE = "select_robot_response"

    # 会话管理
    SESSION_CREATE = "session_create"
    SESSION_CREATED = "session_created"
    SESSION_CLOSE = "session_close"
    SESSION_CLOSED = "session_closed"

    # WebRTC 信令
    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice_candidate"

    # 数据
    ROBOT_STATE = "robot_state"
    JOINT_DELTA = "joint_delta"
    ALERT = "alert"

    # 控制
    TELEOP_COMMAND = "teleop_command"
    JOINT_COMMAND = "joint_command"
    MODE_SWITCH = "mode_switch"
    EMERGENCY_STOP = "emergency_stop"

    # 通用
    ERROR = "error"
    OK = "ok"


@dataclass
class SignalingMessage:
    """信令消息

    符合 qooremote 信令协议规范的通用消息格式。
    """
    type: MessageType = MessageType.OK
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0
    sequence: int = 0
    request_id: str = ""

    def __post_init__(self) -> None:
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "request_id": self.request_id,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> SignalingMessage:
        data = json.loads(json_str)
        return cls(
            type=MessageType(data.get("type", "ok")),
            payload=data.get("payload", {}),
            timestamp=int(data.get("timestamp", 0)),
            sequence=int(data.get("sequence", 0)),
            request_id=str(data.get("request_id", "")),
        )

    @classmethod
    def auth(cls, token: str) -> SignalingMessage:
        """创建认证消息"""
        return cls(type=MessageType.AUTH, payload={"token": token})

    @classmethod
    def heartbeat(cls) -> SignalingMessage:
        return cls(type=MessageType.HEARTBEAT)

    @classmethod
    def list_robots(cls) -> SignalingMessage:
        return cls(type=MessageType.LIST_ROBOTS)

    @classmethod
    def select_robot(cls, robot_id: str) -> SignalingMessage:
        return cls(
            type=MessageType.SELECT_ROBOT,
            payload={"robot_id": robot_id},
        )

    @classmethod
    def robot_state(cls, state_json: str) -> SignalingMessage:
        return cls(
            type=MessageType.ROBOT_STATE,
            payload={"data": json.loads(state_json)},
        )

    @classmethod
    def emergency_stop(cls, reason: str = "operator") -> SignalingMessage:
        return cls(
            type=MessageType.EMERGENCY_STOP,
            payload={"reason": reason},
        )

    @classmethod
    def error(cls, code: int, message: str) -> SignalingMessage:
        return cls(
            type=MessageType.ERROR,
            payload={"code": code, "message": message},
        )
