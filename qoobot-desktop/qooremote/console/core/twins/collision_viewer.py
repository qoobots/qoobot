"""碰撞可视化 — 碰撞检测结果管理与可视化几何

管理碰撞检测结果（碰撞对/接触点/穿透深度/法向），
提供标准化几何基元（球/盒/胶囊）用于渲染。

对应功能 DT-02（碰撞可视化）。
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CollisionShape(str, Enum):
    SPHERE = "sphere"
    BOX = "box"
    CAPSULE = "capsule"
    CYLINDER = "cylinder"
    MESH = "mesh"


@dataclass
class ContactPoint:
    """接触点"""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    penetration_depth: float = 0.0     # 穿透深度 (m)
    contact_force: tuple[float, float, float] = (0.0, 0.0, 0.0)  # 接触力 (N)


@dataclass
class CollisionPair:
    """碰撞对"""
    id: str = ""
    link_a: str = ""
    link_b: str = ""
    is_self_collision: bool = False          # 自碰撞 vs 环境碰撞
    contacts: list[ContactPoint] = field(default_factory=list)
    timestamp: float = 0.0
    severity: float = 0.0                     # 严重程度 (0~1)

    @property
    def max_penetration(self) -> float:
        if not self.contacts:
            return 0.0
        return max(c.penetration_depth for c in self.contacts)


@dataclass
class SafetyZone:
    """安全区域定义"""
    name: str = ""
    shape: CollisionShape = CollisionShape.SPHERE
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    parameters: list[float] = field(default_factory=list)  # 尺寸参数
    color_rgba: tuple[float, float, float, float] = (0.0, 1.0, 0.0, 0.3)  # 绿色半透明
    active: bool = True


@dataclass
class PrimitiveGeometry:
    """渲染几何基元

    标准化后传递给 UI/OpenGL 层渲染。
    """
    shape: CollisionShape = CollisionShape.SPHERE
    # 用户数据（如对应的 URDF link/joint 名）
    tag: str = ""
    # 世界变换
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)  # 四元数 (w,x,y,z)
    # 尺寸参数
    parameters: list[float] = field(default_factory=list)
    # 颜色
    color_rgba: tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0)
    # 线框模式
    wireframe: bool = False
    # 透明度
    opacity: float = 1.0


class CollisionVisualizer:
    """碰撞可视化管理器

    管理碰撞对、安全区域，生成渲染几何基元列表。
    供 3D 视口消费。

    对应功能 DT-02（碰撞可视化）。
    """

    def __init__(self, max_collision_pairs: int = 100) -> None:
        self._collision_pairs: dict[str, CollisionPair] = {}
        self._safety_zones: dict[str, SafetyZone] = {}
        self._max_pairs = max_collision_pairs
        self._history: list[CollisionPair] = []
        self._enabled = True

        # 颜色映射
        self._severity_colors = [
            (0.0, 1.0, 0.0, 0.6),  # 绿色 - 安全
            (1.0, 1.0, 0.0, 0.7),  # 黄色 - 接近
            (1.0, 0.5, 0.0, 0.8),  # 橙色 - 轻微碰撞
            (1.0, 0.0, 0.0, 0.9),  # 红色 - 严重碰撞
        ]

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, val: bool) -> None:
        self._enabled = val

    @property
    def active_pairs(self) -> list[CollisionPair]:
        return list(self._collision_pairs.values())

    @property
    def safety_zones(self) -> list[SafetyZone]:
        return list(self._safety_zones.values())

    def update_collision(self, pair: CollisionPair) -> None:
        """更新/添加碰撞对"""
        pair.timestamp = time.time()
        self._collision_pairs[pair.id] = pair
        # 限制大小
        if len(self._collision_pairs) > self._max_pairs:
            oldest = min(self._collision_pairs.keys(),
                         key=lambda k: self._collision_pairs[k].timestamp)
            old_pair = self._collision_pairs.pop(oldest)
            self._history.append(old_pair)

    def clear_collisions(self) -> None:
        """清除所有活跃碰撞"""
        for pair in list(self._collision_pairs.values()):
            self._history.append(pair)
        self._collision_pairs.clear()

    def add_safety_zone(self, zone: SafetyZone) -> None:
        self._safety_zones[zone.name] = zone

    def remove_safety_zone(self, name: str) -> bool:
        return self._safety_zones.pop(name, None) is not None

    def get_render_primitives(self) -> list[PrimitiveGeometry]:
        """生成碰撞渲染几何基元列表

        Returns:
            PrimitiveGeometry 列表，可直接送往 3D 渲染管线
        """
        primitives: list[PrimitiveGeometry] = []

        if not self._enabled:
            return primitives

        # 碰撞对 → 接触点小球
        for pair in self._collision_pairs.values():
            color = self._severity_color(pair.severity)
            for cp in pair.contacts:
                primitives.append(PrimitiveGeometry(
                    shape=CollisionShape.SPHERE,
                    tag=f"contact_{pair.id}",
                    position=cp.position,
                    parameters=[max(0.005, cp.penetration_depth * 5)],  # 半径与穿透深度成正比
                    color_rgba=color,
                    wireframe=False,
                ))

        # 安全区域
        for zone in self._safety_zones.values():
            if not zone.active:
                continue
            primitives.append(PrimitiveGeometry(
                shape=zone.shape,
                tag=f"safety_{zone.name}",
                position=zone.center,
                parameters=list(zone.parameters),
                color_rgba=zone.color_rgba,
                wireframe=True,
                opacity=0.35,
            ))

        return primitives

    def _severity_color(self, severity: float) -> tuple[float, float, float, float]:
        """根据严重程度返回颜色"""
        idx = min(int(severity * (len(self._severity_colors) - 1)),
                  len(self._severity_colors) - 1)
        return self._severity_colors[idx]

    @staticmethod
    def make_sphere_geometry(center: tuple[float, float, float],
                              radius: float,
                              color: tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0),
                              tag: str = "") -> PrimitiveGeometry:
        """工厂方法：创建球体几何"""
        return PrimitiveGeometry(
            shape=CollisionShape.SPHERE,
            tag=tag,
            position=center,
            parameters=[radius],
            color_rgba=color,
        )

    @staticmethod
    def make_box_geometry(center: tuple[float, float, float],
                           size: tuple[float, float, float],
                           color: tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0),
                           tag: str = "") -> PrimitiveGeometry:
        """工厂方法：创建盒体几何"""
        return PrimitiveGeometry(
            shape=CollisionShape.BOX,
            tag=tag,
            position=center,
            parameters=list(size),
            color_rgba=color,
        )

    def get_statistics(self) -> dict:
        """碰撞统计"""
        active = len(self._collision_pairs)
        self_collisions = sum(1 for p in self._collision_pairs.values() if p.is_self_collision)
        total_contacts = sum(len(p.contacts) for p in self._collision_pairs.values())
        max_pen = max((p.max_penetration for p in self._collision_pairs.values()), default=0.0)

        return {
            "active_pairs": active,
            "self_collisions": self_collisions,
            "env_collisions": active - self_collisions,
            "total_contacts": total_contacts,
            "max_penetration_m": max_pen,
            "safety_zones": len(self._safety_zones),
            "history_count": len(self._history),
        }
