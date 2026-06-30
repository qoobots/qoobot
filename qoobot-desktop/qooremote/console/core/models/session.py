"""会话管理模型 — 遥控会话生命周期、参数配置

对应功能 SES-01（遥控会话生命周期）、SES-02（会话参数配置）。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SessionState(Enum):
    """会话状态"""
    CREATED = "created"        # 已创建
    CONNECTING = "connecting"  # 连接中
    CONNECTED = "connected"    # 已连接
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CLOSED = "closed"


class ControlMode(Enum):
    """控制模式"""
    AUTONOMOUS = "autonomous"        # 自主模式
    SEMI_AUTONOMOUS = "semi_auto"    # 半自主
    MANUAL = "manual"               # 全手动


@dataclass
class SessionConfig:
    """会话参数配置（SES-02）"""
    # 视频
    video_resolution: str = "720p"    # 1080p / 720p / 540p / 480p
    video_fps: int = 30
    video_max_bitrate_kbps: int = 2500
    adaptive_bitrate: bool = True

    # 控制
    control_mode: ControlMode = ControlMode.MANUAL
    control_frequency_hz: int = 50
    deadzone: float = 0.05

    # 延迟
    max_latency_ms: int = 200
    latency_budget_ms: int = 100       # 控制回路延迟预算

    # 安全
    emergency_stop_timeout_ms: int = 500  # 通信中断后多久触发急停
    auto_emergency_stop: bool = True

    # 录制
    auto_record: bool = False

    def to_dict(self) -> dict:
        return {
            "video_resolution": self.video_resolution,
            "video_fps": self.video_fps,
            "video_max_bitrate_kbps": self.video_max_bitrate_kbps,
            "adaptive_bitrate": self.adaptive_bitrate,
            "control_mode": self.control_mode.value,
            "control_frequency_hz": self.control_frequency_hz,
            "deadzone": self.deadzone,
            "max_latency_ms": self.max_latency_ms,
            "latency_budget_ms": self.latency_budget_ms,
            "emergency_stop_timeout_ms": self.emergency_stop_timeout_ms,
            "auto_emergency_stop": self.auto_emergency_stop,
            "auto_record": self.auto_record,
        }


@dataclass
class RobotInfo:
    """机器人基本信息"""
    robot_id: str
    name: str = ""
    model: str = ""
    status: str = "offline"  # online/offline/busy/error
    ip_address: str = ""
    os_version: str = ""
    uptime_s: float = 0.0
    joint_count: int = 28
    camera_count: int = 4

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "name": self.name,
            "model": self.model,
            "status": self.status,
            "ip_address": self.ip_address,
            "os_version": self.os_version,
            "uptime_s": self.uptime_s,
            "joint_count": self.joint_count,
            "camera_count": self.camera_count,
        }


@dataclass
class SessionRecord:
    """历史会话记录（SES-03）"""
    session_id: str
    robot_id: str
    operator: str
    start_time: float
    end_time: Optional[float] = None
    duration_s: float = 0.0
    state: SessionState = SessionState.CREATED
    config: Optional[SessionConfig] = None
    frame_count: int = 0
    data_size_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "robot_id": self.robot_id,
            "operator": self.operator,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": self.duration_s,
            "state": self.state.value,
            "frame_count": self.frame_count,
            "data_size_bytes": self.data_size_bytes,
        }


class Session:
    """遥控会话

    管理一次遥控连接的完整生命周期。
    """

    def __init__(self, robot_id: str, operator: str = "unknown",
                 config: Optional[SessionConfig] = None) -> None:
        self.session_id = str(uuid.uuid4())[:12]
        self.robot_id = robot_id
        self.operator = operator
        self.config = config or SessionConfig()
        self._state = SessionState.CREATED
        self._start_time = time.time()
        self._end_time: Optional[float] = None

        # 回调
        self.on_state_change: callable | None = None

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def duration_s(self) -> float:
        if self._end_time:
            return self._end_time - self._start_time
        return time.time() - self._start_time

    @property
    def is_active(self) -> bool:
        return self._state in (SessionState.CONNECTING, SessionState.CONNECTED)

    def connect(self) -> None:
        self._transition_to(SessionState.CONNECTING)

    def connected(self) -> None:
        self._transition_to(SessionState.CONNECTED)

    def disconnect(self) -> None:
        self._transition_to(SessionState.DISCONNECTING)

    def disconnected(self) -> None:
        self._end_time = time.time()
        self._transition_to(SessionState.DISCONNECTED)

    def error(self) -> None:
        self._end_time = time.time()
        self._transition_to(SessionState.ERROR)

    def close(self) -> None:
        if not self._end_time:
            self._end_time = time.time()
        self._transition_to(SessionState.CLOSED)

    def to_record(self) -> SessionRecord:
        return SessionRecord(
            session_id=self.session_id,
            robot_id=self.robot_id,
            operator=self.operator,
            start_time=self._start_time,
            end_time=self._end_time,
            duration_s=self.duration_s,
            state=self._state,
            config=self.config,
        )

    def _transition_to(self, state: SessionState) -> None:
        old = self._state
        self._state = state
        if old != state and self.on_state_change:
            self.on_state_change(state)


class SessionManager:
    """会话管理器 — 生命周期管理 + 历史记录

    对应功能 SES-01/02/03。
    """

    def __init__(self) -> None:
        self._active_session: Optional[Session] = None
        self._history: list[SessionRecord] = []
        self._config = SessionConfig()

    @property
    def active_session(self) -> Optional[Session]:
        return self._active_session

    @property
    def config(self) -> SessionConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return (self._active_session is not None
                and self._active_session.state == SessionState.CONNECTED)

    @property
    def history(self) -> list[SessionRecord]:
        return list(self._history)

    def create_session(self, robot_id: str, operator: str = "unknown") -> Session:
        """创建新会话"""
        self.close_current()
        self._active_session = Session(robot_id, operator, self._config)
        return self._active_session

    def close_current(self) -> Optional[SessionRecord]:
        """关闭当前会话并归档"""
        if self._active_session:
            self._active_session.close()
            record = self._active_session.to_record()
            self._history.append(record)
            self._active_session = None
            return record
        return None

    def update_config(self, config: SessionConfig) -> None:
        """更新会话配置"""
        self._config = config
        if self._active_session:
            self._active_session.config = config

    def get_history(self, limit: int = 50) -> list[SessionRecord]:
        """获取历史记录"""
        return self._history[-limit:]
