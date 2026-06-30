"""数字孪生核心模块 — URDF/骨架驱动/碰撞/点云/SLAM渲染

提供机器人 3D 数字孪生所需的全部核心计算模型：
- URDF 模型解析与运动学树
- 关节→连杆变换的正向运动学驱动
- 碰撞对检测与可视化几何
- 点云缓冲管理与降采样
- SLAM 地图数据管理

所有模块均为纯 Python 实现，不依赖 OpenGL 等渲染库，
渲染适配器在 UI 层 (viewport_3d.py) 中完成。
"""

from console.core.twins.urdf_loader import URDFModel, URDFLoader, LinkDef, JointDef, JointType, GeometryDef, GeometryType
from console.core.twins.skeleton_driver import SkeletonDriver, LinkPose
from console.core.twins.collision_viewer import CollisionPair, CollisionVisualizer, SafetyZone, CollisionShape
from console.core.twins.pointcloud_renderer import PointCloud, PointCloudManager, PointCloudColorMode, Point
from console.core.twins.slam_renderer import OccupancyGrid, SLAMMap, OctomapNode

__all__ = [
    "URDFModel", "URDFLoader", "LinkDef", "JointDef", "JointType", "GeometryDef", "GeometryType",
    "SkeletonDriver", "LinkPose",
    "CollisionPair", "CollisionVisualizer", "SafetyZone", "CollisionShape",
    "PointCloud", "PointCloudManager", "PointCloudColorMode", "Point",
    "OccupancyGrid", "SLAMMap", "OctomapNode",
]
