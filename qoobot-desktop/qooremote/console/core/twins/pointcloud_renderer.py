"""点云渲染器 — LiDAR/RGB-D 点云数据管理与降采样

管理实时点云缓冲区，支持体素降采样、强度/高度着色映射。
渲染几何输出为标准化顶点列表，供 UI/OpenGL 层使用。

对应功能 DT-03（点云可视化）。
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PointCloudColorMode(str, Enum):
    """点云着色模式"""
    RGB = "rgb"                   # 原始 RGB 颜色
    INTENSITY = "intensity"       # 强度 → 颜色映射（灰度/热力图）
    HEIGHT = "height"             # 高度 → 颜色映射（地形色）
    RANGE = "range"               # 距离 → 颜色映射
    NORMAL = "normal"             # 法向 → 颜色映射


@dataclass
class Point:
    """单个点"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    intensity: float = 1.0        # 归一化强度 [0, 1]
    r: int = 255                  # RGB 颜色
    g: int = 255
    b: int = 255

    @property
    def position(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        return (self.r, self.g, self.b)


@dataclass
class PointCloud:
    """点云帧"""
    frame_id: str = ""
    timestamp: float = 0.0
    points: list[Point] = field(default_factory=list)
    sensor_origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    sensor_orientation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)  # 四元数 (w,x,y,z)
    origin_frame: str = "world"    # 参考坐标系
    has_colors: bool = False
    has_intensity: bool = True
    point_count: int = 0

    def bounds(self) -> dict[str, tuple[float, float]]:
        """计算包围盒"""
        if not self.points:
            return {"x": (0, 0), "y": (0, 0), "z": (0, 0)}
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        zs = [p.z for p in self.points]
        return {
            "x": (min(xs), max(xs)),
            "y": (min(ys), max(ys)),
            "z": (min(zs), max(zs)),
        }


class PointCloudManager:
    """点云管理器

    维护最近 N 帧点云缓冲区，支持：
    - 体素网格降采样
    - 多种颜色映射
    - 帧融合/累积
    - 顶点缓冲生成（供 OpenGL 渲染）

    对应功能 DT-03（点云可视化）。
    """

    def __init__(self, max_frames: int = 10, max_points_per_frame: int = 500000) -> None:
        self._max_frames = max_frames
        self._max_points_per_frame = max_points_per_frame
        self._frames: list[PointCloud] = []
        self._current_color_mode: PointCloudColorMode = PointCloudColorMode.INTENSITY
        self._voxel_size: float = 0.05           # 体素降采样大小 (m)
        self._enable_downsample: bool = True
        self._accumulate_frames: bool = False
        self._point_size: float = 2.0

    @property
    def color_mode(self) -> PointCloudColorMode:
        return self._current_color_mode

    @color_mode.setter
    def color_mode(self, mode: PointCloudColorMode) -> None:
        self._current_color_mode = mode

    @property
    def voxel_size(self) -> float:
        return self._voxel_size

    @voxel_size.setter
    def voxel_size(self, size: float) -> None:
        self._voxel_size = max(0.001, size)

    @property
    def accumulate(self) -> bool:
        return self._accumulate_frames

    @accumulate.setter
    def accumulate(self, val: bool) -> None:
        self._accumulate_frames = val

    @property
    def point_size(self) -> float:
        return self._point_size

    @point_size.setter
    def point_size(self, val: float) -> None:
        self._point_size = max(0.5, min(20.0, val))

    def add_frame(self, cloud: PointCloud) -> None:
        """添加一帧点云"""
        cloud.timestamp = time.time()
        if len(cloud.points) > self._max_points_per_frame:
            cloud.points = cloud.points[:self._max_points_per_frame]

        self._frames.append(cloud)
        if len(self._frames) > self._max_frames:
            self._frames = self._frames[-self._max_frames:]

    def get_latest_cloud(self) -> Optional[PointCloud]:
        """获取最新点云帧"""
        return self._frames[-1] if self._frames else None

    def clear(self) -> None:
        self._frames.clear()

    def get_vertex_buffer(self) -> tuple[list[float], list[float], int]:
        """生成顶点缓冲 + 颜色缓冲

        Returns:
            (vertices: [x,y,z,...], colors: [r,g,b,...], point_count)
        """
        if self._accumulate_frames:
            all_points = [p for f in self._frames for p in f.points]
        elif self._frames:
            all_points = list(self._frames[-1].points)
        else:
            return [], [], 0

        if self._enable_downsample and self._voxel_size > 0:
            all_points = self._voxel_downsample(all_points, self._voxel_size)

        vertices: list[float] = []
        colors: list[float] = []

        for p in all_points:
            vertices.extend([p.x, p.y, p.z])
            cr, cg, cb = self._map_color(p)
            colors.extend([cr / 255.0, cg / 255.0, cb / 255.0])

        return vertices, colors, len(all_points)

    def _map_color(self, p: Point) -> tuple[int, int, int]:
        """按当前颜色模式映射颜色"""
        if self._current_color_mode == PointCloudColorMode.RGB and p.r + p.g + p.b > 0:
            return (p.r, p.g, p.b)

        if self._current_color_mode == PointCloudColorMode.INTENSITY:
            return self._intensity_to_color(p.intensity)

        if self._current_color_mode == PointCloudColorMode.HEIGHT:
            # 需要知道点云高度范围才能准确映射
            return self._height_to_color(p.z, -2.0, 2.0)

        if self._current_color_mode == PointCloudColorMode.RANGE:
            dist = math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)
            return self._height_to_color(dist, 0.0, 30.0)

        return (255, 255, 255)

    @staticmethod
    def _intensity_to_color(intensity: float) -> tuple[int, int, int]:
        """强度 → 热力图颜色"""
        v = max(0.0, min(1.0, intensity))
        if v < 0.25:
            t = v * 4
            return (0, int(255 * t), 255)
        elif v < 0.5:
            t = (v - 0.25) * 4
            return (0, 255, int(255 * (1 - t)))
        elif v < 0.75:
            t = (v - 0.5) * 4
            return (int(255 * t), 255, 0)
        else:
            t = (v - 0.75) * 4
            return (255, int(255 * (1 - t)), 0)

    @staticmethod
    def _height_to_color(z: float, zmin: float, zmax: float) -> tuple[int, int, int]:
        """高度 → 地形颜色映射"""
        span = zmax - zmin
        if span < 1e-9:
            v = 0.5
        else:
            v = max(0.0, min(1.0, (z - zmin) / span))

        if v < 0.2:   # 蓝→青
            t = v / 0.2
            return (0, int(100 + 155 * t), int(100 + 155 * t))
        elif v < 0.4:  # 青→绿
            t = (v - 0.2) / 0.2
            return (0, int(255 - 100 * t), int(255 - 100 * t))
        elif v < 0.6:  # 绿→黄
            t = (v - 0.4) / 0.2
            return (int(255 * t), 155 + int(100 * t), 0)
        elif v < 0.8:  # 黄→红
            t = (v - 0.6) / 0.2
            return (255, int(255 * (1 - t)), 0)
        else:           # 红→白
            t = (v - 0.8) / 0.2
            return (255, int(255 * t), int(255 * t))

    @staticmethod
    def _voxel_downsample(points: list[Point], voxel_size: float) -> list[Point]:
        """体素网格降采样 — 每个体素保留强度最大的点"""
        if not points or voxel_size <= 0:
            return points

        voxels: dict[tuple[int, int, int], Point] = {}
        inv = 1.0 / voxel_size

        for p in points:
            key = (int(math.floor(p.x * inv)),
                   int(math.floor(p.y * inv)),
                   int(math.floor(p.z * inv)))
            existing = voxels.get(key)
            if existing is None or p.intensity > existing.intensity:
                voxels[key] = p

        return list(voxels.values())

    def get_statistics(self) -> dict:
        """点云统计信息"""
        latest = self.get_latest_cloud()
        total_points = sum(len(f.points) for f in self._frames)
        return {
            "frames_buffered": len(self._frames),
            "total_points": total_points,
            "latest_frame_points": len(latest.points) if latest else 0,
            "accumulate": self._accumulate_frames,
            "voxel_size_m": self._voxel_size,
            "downsample_enabled": self._enable_downsample,
            "color_mode": self._current_color_mode.value,
        }
