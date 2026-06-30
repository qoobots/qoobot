"""机器人状态数据模型

定义机器人状态快照、系统状态、电源信息、IMU 数据和力传感器数据的
结构化数据类，支持 JSON 序列化/反序列化。

每 30Hz 由机器人端通过 DataChannel 推送完整状态快照。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from console.core.models.joint_state import JointState
from console.core.models.alert import Alert


class RobotMode(str, Enum):
    """机器人操控模式"""
    AUTONOMOUS = "autonomous"       # 全自主
    SEMI_AUTONOMOUS = "semi_autonomous"  # 半自主
    MANUAL = "manual"               # 全手动
    EMERGENCY = "emergency"         # 紧急状态
    IDLE = "idle"                   # 空闲


class RobotOperationalState(str, Enum):
    """机器人运行状态"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    INITIALIZING = "initializing"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class CpuTemperature:
    """CPU 温度信息"""
    soc: float = 0.0          # SoC 芯片温度 (Celsius)
    ambient: float = 0.0      # 环境温度 (Celsius)


@dataclass
class RobotStatus:
    """机器人系统状态"""
    mode: RobotMode = RobotMode.IDLE
    state: RobotOperationalState = RobotOperationalState.STOPPED
    uptime_seconds: float = 0.0
    cpu_percent: float = 0.0           # CPU 使用率 (%)
    memory_used_mb: float = 0.0        # 已用内存 (MB)
    memory_total_mb: float = 0.0       # 总内存 (MB)
    disk_used_gb: float = 0.0          # 已用磁盘 (GB)
    disk_total_gb: float = 0.0         # 总磁盘 (GB)
    temperature: CpuTemperature = field(default_factory=CpuTemperature)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "state": self.state.value,
            "uptime_seconds": self.uptime_seconds,
            "cpu_percent": self.cpu_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "disk_used_gb": self.disk_used_gb,
            "disk_total_gb": self.disk_total_gb,
            "temperature_celsius": {
                "soc": self.temperature.soc,
                "ambient": self.temperature.ambient,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RobotStatus:
        temp_data = data.get("temperature_celsius", {})
        return cls(
            mode=RobotMode(data.get("mode", "idle")),
            state=RobotOperationalState(data.get("state", "stopped")),
            uptime_seconds=float(data.get("uptime_seconds", 0)),
            cpu_percent=float(data.get("cpu_percent", 0)),
            memory_used_mb=float(data.get("memory_used_mb", 0)),
            memory_total_mb=float(data.get("memory_total_mb", 8192)),
            disk_used_gb=float(data.get("disk_used_gb", 0)),
            disk_total_gb=float(data.get("disk_total_gb", 256)),
            temperature=CpuTemperature(
                soc=float(temp_data.get("soc", 0)),
                ambient=float(temp_data.get("ambient", 0)),
            ),
        )


@dataclass
class BatteryCell:
    """电池单体信息"""
    id: int = 0
    voltage: float = 0.0       # 电压 (V)
    temperature: float = 0.0   # 温度 (Celsius)


@dataclass
class PowerInfo:
    """电源与电池信息"""
    battery_percent: float = 100.0        # 电量百分比
    charging: bool = False                 # 是否充电中
    voltage: float = 0.0                  # 总线电压 (V)
    current_amps: float = 0.0             # 电流 (A)
    power_watts: float = 0.0              # 功耗 (W)
    estimated_runtime_minutes: float = 0.0  # 预估剩余续航 (分钟)
    cells: list[BatteryCell] = field(default_factory=list)

    @property
    def is_low_battery(self) -> bool:
        """是否电量不足 (< 20%)"""
        return self.battery_percent < 20.0

    @property
    def is_critical_battery(self) -> bool:
        """是否电量严重不足 (< 5%)"""
        return self.battery_percent < 5.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "battery_percent": self.battery_percent,
            "charging": self.charging,
            "voltage": self.voltage,
            "current_amps": self.current_amps,
            "power_watts": self.power_watts,
            "estimated_runtime_minutes": self.estimated_runtime_minutes,
            "cells": [
                {"id": c.id, "voltage": c.voltage, "temperature": c.temperature}
                for c in self.cells
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PowerInfo:
        cells = [
            BatteryCell(
                id=int(c.get("id", 0)),
                voltage=float(c.get("voltage", 0)),
                temperature=float(c.get("temperature", 0)),
            )
            for c in data.get("cells", [])
        ]
        return cls(
            battery_percent=float(data.get("battery_percent", 100)),
            charging=bool(data.get("charging", False)),
            voltage=float(data.get("voltage", 0)),
            current_amps=float(data.get("current_amps", 0)),
            power_watts=float(data.get("power_watts", 0)),
            estimated_runtime_minutes=float(data.get("estimated_runtime_minutes", 0)),
            cells=cells,
        )


@dataclass
class Quaternion:
    """四元数"""
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_list(self) -> list[float]:
        return [self.w, self.x, self.y, self.z]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Quaternion:
        return cls(
            w=float(data.get("w", 1.0)),
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            z=float(data.get("z", 0.0)),
        )


@dataclass
class Vector3:
    """三维向量"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vector3:
        return cls(
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            z=float(data.get("z", 0.0)),
        )


@dataclass
class ImuData:
    """IMU 惯性测量数据"""
    orientation: Quaternion = field(default_factory=Quaternion)
    angular_velocity: Vector3 = field(default_factory=Vector3)
    linear_acceleration: Vector3 = field(default_factory=Vector3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "orientation": {"w": self.orientation.w, "x": self.orientation.x,
                            "y": self.orientation.y, "z": self.orientation.z},
            "angular_velocity": {"x": self.angular_velocity.x,
                                 "y": self.angular_velocity.y,
                                 "z": self.angular_velocity.z},
            "linear_acceleration": {"x": self.linear_acceleration.x,
                                    "y": self.linear_acceleration.y,
                                    "z": self.linear_acceleration.z},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImuData:
        return cls(
            orientation=Quaternion.from_dict(data.get("orientation", {})),
            angular_velocity=Vector3.from_dict(data.get("angular_velocity", {})),
            linear_acceleration=Vector3.from_dict(data.get("linear_acceleration", {})),
        )


@dataclass
class ForceData:
    """力传感器数据"""
    sensor: str = ""         # 传感器名称, e.g. "left_foot_fz"
    value_n: float = 0.0     # 力值 (N)

    def to_dict(self) -> dict[str, Any]:
        return {"sensor": self.sensor, "value_n": self.value_n}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForceData:
        return cls(
            sensor=str(data.get("sensor", "")),
            value_n=float(data.get("value_n", 0.0)),
        )


@dataclass
class RobotState:
    """机器人完整状态快照

    机器人端通过 DataChannel 以 30Hz 频率推送。
    """
    timestamp: int = 0              # Unix 毫秒时间戳
    sequence: int = 0               # 序列号（用于丢包检测）
    robot_id: str = ""              # 机器人唯一标识
    status: RobotStatus = field(default_factory=RobotStatus)
    power: PowerInfo = field(default_factory=PowerInfo)
    joints: list[JointState] = field(default_factory=list)
    imu: ImuData = field(default_factory=ImuData)
    forces: list[ForceData] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "robot_id": self.robot_id,
            "status": self.status.to_dict(),
            "power": self.power.to_dict(),
            "joints": [j.to_dict() for j in self.joints],
            "imu": self.imu.to_dict(),
            "forces": [f.to_dict() for f in self.forces],
            "alerts": [a.to_dict() for a in self.alerts],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RobotState:
        return cls(
            timestamp=int(data.get("timestamp", 0)),
            sequence=int(data.get("sequence", 0)),
            robot_id=str(data.get("robot_id", "")),
            status=RobotStatus.from_dict(data.get("status", {})),
            power=PowerInfo.from_dict(data.get("power", {})),
            joints=[JointState.from_dict(j) for j in data.get("joints", [])],
            imu=ImuData.from_dict(data.get("imu", {})),
            forces=[ForceData.from_dict(f) for f in data.get("forces", [])],
            alerts=[Alert.from_dict(a) for a in data.get("alerts", [])],
        )

    @classmethod
    def from_json(cls, json_str: str) -> RobotState:
        return cls.from_dict(json.loads(json_str))
