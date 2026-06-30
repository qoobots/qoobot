"""关节状态数据模型"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class JointStatus(str, Enum):
    """关节状态枚举"""
    NORMAL = "normal"
    WARNING = "warning"           # 过温/过流警告
    ERROR = "error"               # 故障
    DISABLED = "disabled"         # 已禁用
    CALIBRATING = "calibrating"   # 校准中


@dataclass
class JointState:
    """单个关节状态

    包含位置、速度、力矩、温度、电流等关节实时数据。
    """
    name: str = ""                        # 关节名称, e.g. "left_shoulder_pitch"
    id: int = 0                           # 关节 ID
    position_rad: float = 0.0             # 当前位置 (rad)
    velocity_rad_s: float = 0.0           # 当前速度 (rad/s)
    torque_nm: float = 0.0                # 当前力矩 (Nm)
    temperature_celsius: float = 0.0      # 温度 (Celsius)
    current_amps: float = 0.0             # 电流 (A)
    status: JointStatus = JointStatus.NORMAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "id": self.id,
            "position_rad": self.position_rad,
            "velocity_rad_s": self.velocity_rad_s,
            "torque_nm": self.torque_nm,
            "temperature_celsius": self.temperature_celsius,
            "current_amps": self.current_amps,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JointState:
        return cls(
            name=str(data.get("name", "")),
            id=int(data.get("id", 0)),
            position_rad=float(data.get("position_rad", 0.0)),
            velocity_rad_s=float(data.get("velocity_rad_s", 0.0)),
            torque_nm=float(data.get("torque_nm", 0.0)),
            temperature_celsius=float(data.get("temperature_celsius", 0.0)),
            current_amps=float(data.get("current_amps", 0.0)),
            status=JointStatus(data.get("status", "normal")),
        )
