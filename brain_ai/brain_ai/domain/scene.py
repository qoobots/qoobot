"""
brain_ai/domain/scene.py — Scene graph and 3D perception entities.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def norm(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]


@dataclass
class Quaternion:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z, self.w]


@dataclass
class Pose6D:
    position: Vec3 = field(default_factory=Vec3)
    orientation: Quaternion = field(default_factory=Quaternion)

    def to_list(self) -> list[float]:
        return self.position.to_list() + self.orientation.to_list()


@dataclass
class BoundingBox3D:
    """Axis-aligned 3D bounding box."""
    center: Vec3 = field(default_factory=Vec3)
    size: Vec3 = field(default_factory=Vec3)    # width, height, depth

    @property
    def volume(self) -> float:
        return self.size.x * self.size.y * self.size.z


@dataclass
class DetectedObject:
    """A single object detected by the perception pipeline."""
    id: str = ""
    label: str = ""                       # e.g. "red_cup", "table", "bottle"
    confidence: float = 0.0
    pose: Pose6D = field(default_factory=Pose6D)
    bbox: BoundingBox3D = field(default_factory=BoundingBox3D)
    track_id: Optional[str] = None        # stable multi-frame tracking ID
    graspable: bool = True
    attributes: dict = field(default_factory=dict)  # color, material, etc.

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "position": self.pose.position.to_list(),
            "graspable": self.graspable,
        }


@dataclass
class OccupancyVoxelGrid:
    """Binary 3D occupancy map (simplified)."""
    resolution_m: float = 0.05          # 5 cm voxels
    origin: Vec3 = field(default_factory=Vec3)
    dims: tuple[int, int, int] = (100, 100, 50)
    data: bytes = b""                   # 1 byte per voxel: 0=free, 1=occupied


@dataclass
class SceneGraph:
    """Aggregated scene understanding from all perception sources."""
    timestamp: datetime = field(default_factory=datetime.now)
    objects: list[DetectedObject] = field(default_factory=list)
    robot_pose: Pose6D = field(default_factory=Pose6D)
    occupancy: Optional[OccupancyVoxelGrid] = None
    source_frame: str = "world"

    def get_object(self, label: str) -> Optional[DetectedObject]:
        """Return first object matching label, or None."""
        for obj in self.objects:
            if obj.label.lower() == label.lower():
                return obj
        return None

    def get_graspable_objects(self) -> list[DetectedObject]:
        return [o for o in self.objects if o.graspable]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "robot_pose": self.robot_pose.to_list(),
            "objects": [o.to_dict() for o in self.objects],
            "object_count": len(self.objects),
        }
