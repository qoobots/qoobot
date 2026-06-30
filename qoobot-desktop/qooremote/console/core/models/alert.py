"""告警数据模型"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重


class AlertType(str, Enum):
    """告警类型"""
    BATTERY_LOW = "battery_low"
    BATTERY_CRITICAL = "battery_critical"
    MOTOR_OVERTEMP = "motor_overtemp"
    CPU_OVERTEMP = "cpu_overtemp"
    COLLISION_DETECTED = "collision_detected"
    COMMUNICATION_LOST = "communication_lost"
    JOINT_FAULT = "joint_fault"
    IMU_FAULT = "imu_fault"
    SAFETY_VIOLATION = "safety_violation"
    TORQUE_LIMIT = "torque_limit"
    SELF_COLLISION = "self_collision"
    SYSTEM_ERROR = "system_error"


@dataclass
class Alert:
    """告警通知"""
    id: str = ""                          # 告警唯一 ID
    level: AlertLevel = AlertLevel.INFO   # 告警级别
    type: AlertType = AlertType.SYSTEM_ERROR  # 告警类型
    message: str = ""                     # 告警消息
    timestamp: int = 0                    # Unix 毫秒时间戳
    acknowledged: bool = False            # 是否已确认
    acknowledged_at: int = 0              # 确认时间戳
    source: str = ""                      # 来源模块, e.g. "motor_driver"

    @classmethod
    def create(
        cls,
        level: AlertLevel,
        alert_type: AlertType,
        message: str,
        source: str = "",
        alert_id: str = "",
    ) -> Alert:
        """工厂方法：创建新告警"""
        import uuid
        return cls(
            id=alert_id or f"alt-{uuid.uuid4().hex[:8]}",
            level=level,
            type=alert_type,
            message=message,
            timestamp=int(time.time() * 1000),
            source=source,
        )

    def acknowledge(self) -> None:
        """标记为已确认"""
        self.acknowledged = True
        self.acknowledged_at = int(time.time() * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level.value,
            "type": self.type.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Alert:
        return cls(
            id=str(data.get("id", "")),
            level=AlertLevel(data.get("level", "info")),
            type=AlertType(data.get("type", "system_error")),
            message=str(data.get("message", "")),
            timestamp=int(data.get("timestamp", 0)),
            acknowledged=bool(data.get("acknowledged", False)),
            acknowledged_at=int(data.get("acknowledged_at", 0)),
            source=str(data.get("source", "")),
        )


class AlertManager:
    """告警管理器

    管理活跃告警列表和历史记录，提供告警添加/确认/清除功能。
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._active: dict[str, Alert] = {}
        self._history: list[Alert] = []
        self._max_history = max_history
        self._on_new_alert: list[callable] = []   # type: ignore
        self._on_alert_cleared: list[callable] = []  # type: ignore

    @property
    def active_alerts(self) -> list[Alert]:
        return list(self._active.values())

    @property
    def history(self) -> list[Alert]:
        return list(self._history)

    def add_listener(self, on_new: callable) -> None:  # type: ignore
        """注册新告警回调"""
        self._on_new_alert.append(on_new)

    def add_clear_listener(self, on_clear: callable) -> None:  # type: ignore
        """注册告警清除回调"""
        self._on_alert_cleared.append(on_clear)

    def add_alert(self, alert: Alert) -> None:
        """添加告警"""
        self._active[alert.id] = alert
        self._history.append(alert)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        for callback in self._on_new_alert:
            callback(alert)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        alert = self._active.get(alert_id)
        if alert:
            alert.acknowledge()
            return True
        return False

    def clear_alert(self, alert_id: str) -> bool:
        """清除告警"""
        if alert_id in self._active:
            del self._active[alert_id]
            for callback in self._on_alert_cleared:
                callback(alert_id)
            return True
        return False

    def clear_all(self) -> None:
        """清除所有活跃告警"""
        for alert_id in list(self._active.keys()):
            self.clear_alert(alert_id)

    def get_by_level(self, level: AlertLevel) -> list[Alert]:
        """按级别获取告警"""
        return [a for a in self._active.values() if a.level == level]

    @property
    def critical_count(self) -> int:
        return len(self.get_by_level(AlertLevel.CRITICAL))

    @property
    def error_count(self) -> int:
        return len(self.get_by_level(AlertLevel.ERROR))

    @property
    def warning_count(self) -> int:
        return len(self.get_by_level(AlertLevel.WARNING))
