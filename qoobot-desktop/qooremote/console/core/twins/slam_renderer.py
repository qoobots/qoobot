"""SLAM 地图渲染 — 环境 3D 重建显示

管理 SLAM 建图数据（占用栅格地图 / OctoMap），
生成渲染网格几何体供 OpenGL 显示。

对应功能 DT-04（环境3D重建）。
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MapType(str, Enum):
    OCCUPANCY_GRID_2D = "occupancy_grid_2d"   # 2D 占用栅格地图
    OCTOMAP_3D = "octomap_3d"                  # 3D 八叉树地图
    MESH = "mesh"                              # 三角网格重建
    TSDF = "tsdf"                              # 截断符号距离函数


@dataclass
class OccupancyGrid:
    """2D 占用栅格地图

    用于地面机器人 SLAM 建图结果显示。
    """
    width: int = 0              # 像素宽度
    height: int = 0             # 像素高度
    resolution: float = 0.05    # 米/像素
    origin_x: float = 0.0       # 地图原点世界坐标 (左下角)
    origin_y: float = 0.0
    data: list[int] = field(default_factory=list)  # 逐像素占用值 [0, 100]，-1=未知
    timestamp: float = 0.0
    frame_id: str = "map"

    def pixel_to_world(self, px: int, py: int) -> tuple[float, float]:
        """像素坐标→世界坐标"""
        return (
            self.origin_x + px * self.resolution,
            self.origin_y + py * self.resolution,
        )

    def world_to_pixel(self, wx: float, wy: float) -> tuple[int, int]:
        """世界坐标→像素坐标"""
        return (
            int((wx - self.origin_x) / self.resolution),
            int((wy - self.origin_y) / self.resolution),
        )

    @property
    def width_meters(self) -> float:
        return self.width * self.resolution

    @property
    def height_meters(self) -> float:
        return self.height * self.resolution

    @property
    def center_world(self) -> tuple[float, float]:
        return (
            self.origin_x + self.width_meters / 2,
            self.origin_y + self.height_meters / 2,
        )


@dataclass
class OctomapNode:
    """八叉树节点

    用于 3D 环境建模（无人机 / 机械臂工作空间）。
    """
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: float = 0.1            # 节点半边长 (m)
    occupancy: float = 0.5       # 占用概率 [0, 1]
    is_leaf: bool = True

    def occupied(self, threshold: float = 0.5) -> bool:
        return self.occupancy >= threshold

    def free(self, threshold: float = 0.5) -> bool:
        return self.occupancy < (1.0 - threshold)


@dataclass
class OctomapData:
    """八叉树地图"""
    nodes: list[OctomapNode] = field(default_factory=list)
    resolution: float = 0.1      # 最小节点尺寸 (m)
    tree_depth: int = 16
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp: float = 0.0
    frame_id: str = "map"


@dataclass
class TriangleMesh:
    """三角网格"""
    vertices: list[float] = field(default_factory=list)    # [x0,y0,z0, x1,y1,z1, ...]
    normals: list[float] = field(default_factory=list)     # [nx0,ny0,nz0, ...]
    indices: list[int] = field(default_factory=list)       # [i0,i1,i2, ...]
    vertex_count: int = 0
    triangle_count: int = 0


class SLAMMap:
    """SLAM 地图管理器

    聚合多种环境重建数据，提供统一访问接口。
    支持 2D 栅格地图 + 3D 八叉树 + 三角网格。

    对应功能 DT-04（环境3D重建）。
    """

    def __init__(self) -> None:
        self._occupancy_grid: Optional[OccupancyGrid] = None
        self._octomap: Optional[OctomapData] = None
        self._mesh: Optional[TriangleMesh] = None

        # 渲染选项
        self._show_grid: bool = True
        self._show_octomap: bool = True
        self._show_mesh: bool = True
        self._occupancy_threshold: float = 0.5
        self._grid_height_offset: float = 0.01  # 2D 网格在地面上的偏移

    @property
    def occupancy_grid(self) -> Optional[OccupancyGrid]:
        return self._occupancy_grid

    @occupancy_grid.setter
    def occupancy_grid(self, grid: Optional[OccupancyGrid]) -> None:
        if grid:
            grid.timestamp = time.time()
        self._occupancy_grid = grid

    @property
    def octomap(self) -> Optional[OctomapData]:
        return self._octomap

    @octomap.setter
    def octomap(self, omap: Optional[OctomapData]) -> None:
        if omap:
            omap.timestamp = time.time()
        self._octomap = omap

    @property
    def mesh(self) -> Optional[TriangleMesh]:
        return self._mesh

    @mesh.setter
    def mesh(self, m: Optional[TriangleMesh]) -> None:
        self._mesh = m

    # 渲染开关
    @property
    def show_grid(self) -> bool:
        return self._show_grid
    @show_grid.setter
    def show_grid(self, v: bool) -> None:
        self._show_grid = v

    @property
    def show_octomap(self) -> bool:
        return self._show_octomap
    @show_octomap.setter
    def show_octomap(self, v: bool) -> None:
        self._show_octomap = v

    @property
    def show_mesh(self) -> bool:
        return self._show_mesh
    @show_mesh.setter
    def show_mesh(self, v: bool) -> None:
        self._show_mesh = v

    def occupancy_grid_to_quads(self) -> tuple[list[float], list[float], int]:
        """将 2D 栅格地图转换为四边形网格顶点+颜色数据

        占用→红色，空闲→绿色，未知→灰色。

        Returns:
            (vertices, colors, vertex_count)
        """
        grid = self._occupancy_grid
        if grid is None or grid.width == 0 or grid.height == 0:
            return [], [], 0

        vertices: list[float] = []
        colors: list[float] = []
        res = grid.resolution
        z = self._grid_height_offset

        for py in range(grid.height):
            for px in range(grid.width):
                idx = py * grid.width + px
                if idx >= len(grid.data):
                    continue
                val = grid.data[idx]
                if val < 0:      # 未知
                    color = (0.5, 0.5, 0.5)
                elif val < 50:    # 空闲
                    color = (0.1, 0.6, 0.1)
                else:             # 占用
                    color = (0.8, 0.1, 0.1)

                wx, wy = grid.pixel_to_world(px, py)
                # 四边形 (两个三角形)
                v = [
                    wx, wy, z,
                    wx + res, wy, z,
                    wx + res, wy + res, z,
                    wx, wy + res, z,
                ]
                c = [color[0], color[1], color[2]] * 4
                vertices.extend(v)
                colors.extend(c)

        return vertices, colors, len(vertices) // 3

    def octomap_to_cubes(self) -> tuple[list[float], list[float], list[int], int]:
        """将八叉树地图转换为盒子网格

        仅输出占用的叶子节点。

        Returns:
            (vertices, colors, indices, vertex_count)
        """
        omap = self._octomap
        if omap is None or not omap.nodes:
            return [], [], [], 0

        vertices: list[float] = []
        colors: list[float] = []
        indices: list[int] = []
        vi = 0

        for node in omap.nodes:
            if not node.is_leaf or not node.occupied(self._occupancy_threshold):
                continue

            cx, cy, cz = node.center
            s = node.size

            # 8 个顶点
            verts_local = [
                (-s, -s, -s), ( s, -s, -s), ( s,  s, -s), (-s,  s, -s),
                (-s, -s,  s), ( s, -s,  s), ( s,  s,  s), (-s,  s,  s),
            ]
            for vx, vy, vz in verts_local:
                vertices.extend([cx + vx, cy + vy, cz + vz])

            # 占用概率 → 颜色 (蓝→红)
            t = node.occupancy
            r = 0.1 + 0.7 * t
            g = 0.2 + 0.3 * (1 - t)
            b = 0.5 + 0.3 * (1 - t)
            colors.extend([r, g, b] * 8)

            # 12 个三角形索引
            cube_indices = [
                0,1,2, 0,2,3,  # 前
                4,6,5, 4,7,6,  # 后
                0,4,5, 0,5,1,  # 下
                2,6,7, 2,7,3,  # 上
                0,3,7, 0,7,4,  # 左
                1,5,6, 1,6,2,  # 右
            ]
            for idx in cube_indices:
                indices.append(vi + idx)
            vi += 8

        return vertices, colors, indices, vi

    def get_statistics(self) -> dict:
        """地图统计"""
        stats: dict = {
            "grid_2d": None,
            "octomap_3d": None,
            "mesh": None,
        }
        if self._occupancy_grid:
            g = self._occupancy_grid
            stats["grid_2d"] = {
                "size": f"{g.width}x{g.height}",
                "resolution_m": g.resolution,
                "area_m2": g.width_meters * g.height_meters,
            }
        if self._octomap:
            om = self._octomap
            occupied = sum(1 for n in om.nodes if n.is_leaf and n.occupied())
            stats["octomap_3d"] = {
                "total_nodes": len(om.nodes),
                "occupied_leaf_nodes": occupied,
                "resolution_m": om.resolution,
                "depth": om.tree_depth,
            }
        if self._mesh:
            stats["mesh"] = {
                "vertices": self._mesh.vertex_count,
                "triangles": self._mesh.triangle_count,
            }
        return stats
