"""传感器数据模型 — 聚合非 IMU 的传感器读数"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SensorReading:
    """单个传感器读数"""
    name: str = ""         # 传感器名称
    value: float = 0.0     # 传感器数值
    unit: str = ""         # 单位, e.g. "N", "Pa", "lux", "dB"

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value, "unit": self.unit}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensorReading:
        return cls(
            name=str(data.get("name", "")),
            value=float(data.get("value", 0.0)),
            unit=str(data.get("unit", "")),
        )


@dataclass
class SensorData:
    """传感器数据聚合

    包含 IMU 之外的各类传感器读数（力传感器、触觉、超声波、
    激光测距等），由 core.models.robot_state.ImuData 单独管理 IMU。
    """
    timestamp: int = 0
    readings: list[SensorReading] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "readings": [r.to_dict() for r in self.readings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensorData:
        return cls(
            timestamp=int(data.get("timestamp", 0)),
            readings=[SensorReading.from_dict(r) for r in data.get("readings", [])],
        )
