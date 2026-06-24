"""brain_os SDK — 公共数据类型"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Quaternion:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0


@dataclass
class Pose:
    position: Vector3 = field(default_factory=Vector3)
    orientation: Quaternion = field(default_factory=Quaternion)


@dataclass
class BoundingBox3D:
    center: Pose = field(default_factory=Pose)
    dimensions: Vector3 = field(default_factory=Vector3)


@dataclass
class RobotInfo:
    robot_id: str = ""
    model_name: str = ""
    serial_no: str = ""
    firmware: str = ""


@dataclass
class StatusResult:
    """gRPC 调用结果包装。"""
    ok: bool = True
    code: int = 0
    message: str = ""
    data: Optional[object] = None
