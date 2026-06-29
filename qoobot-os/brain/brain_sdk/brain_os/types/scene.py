"""场景理解数据类型。

包括场景图、三维目标、语义标签、空间关系等。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from brain_os.types.common import BoundingBox3D, Pose


@dataclass
class SemanticLabel:
    """语义标签。

    Attributes:
        category: 主类别 (e.g. "cup", "table", "robot")
        attributes: 属性键值对 (e.g. {"color": "red", "material": "plastic"})
        confidence: 分类置信度 (0.0-1.0)
    """

    category: str
    attributes: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class Object3D:
    """三维目标对象。

    Attributes:
        id: 唯一标识符
        label: 语义标签
        pose: 6-DoF 位姿 (世界坐标系)
        bbox: 3D 包围盒
        mesh_url: 网格文件路径或 URL
        properties: 物理属性 (mass_kg, friction 等)
    """

    id: str = field(default_factory=lambda: f"obj_{uuid.uuid4().hex[:8]}")
    label: Optional[SemanticLabel] = None
    pose: Optional[Pose] = None
    bbox: Optional[BoundingBox3D] = None
    mesh_url: str = ""
    properties: Dict[str, float] = field(default_factory=dict)


@dataclass
class SpatialRelation:
    """空间关系描述。

    Attributes:
        type: 关系类型 (e.g. "on", "inside", "beside", "in_front_of")
        subject_id: 主体对象 ID
        object_id: 客体对象 ID
        distance_m: 两点间距离 (米)
        normal: 方向法向量
    """

    type: str
    subject_id: str
    object_id: str
    distance_m: float = 0.0
    normal: Optional[Tuple[float, float, float]] = None


@dataclass
class SceneGraph:
    """场景图。

    Attributes:
        objects: 场景中所有对象
        relations: 对象间空间关系列表
        timestamp_ms: 场景时间戳 (毫秒)
        scene_id: 场景唯一标识
        raw_cloud_url: 原始点云数据路径
    """

    objects: List[Object3D] = field(default_factory=list)
    relations: List[SpatialRelation] = field(default_factory=list)
    timestamp_ms: int = 0
    scene_id: str = field(default_factory=lambda: f"scene_{uuid.uuid4().hex[:8]}")
    raw_cloud_url: str = ""


@dataclass
class SceneQuery:
    """场景查询请求。

    Attributes:
        target_label: 目标语义标签 (支持通配符)
        spatial_constraints: 空间约束条件
        min_confidence: 最小置信度阈值
        max_results: 最大返回结果数
    """

    target_label: str = "*"
    spatial_constraints: List[str] = field(default_factory=list)
    min_confidence: float = 0.5
    max_results: int = 10


@dataclass
class SceneQueryResult:
    """场景查询结果。

    Attributes:
        query: 原始查询
        matches: 匹配到的对象列表
        total_found: 符合条件的对象总数
    """

    query: Optional[SceneQuery] = None
    matches: List[Object3D] = field(default_factory=list)
    total_found: int = 0
