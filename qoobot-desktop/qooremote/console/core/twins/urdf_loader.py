"""URDF 模型加载器 — 解析机器人 URDF 描述文件

纯 Python 实现，不依赖外部 XML 库以外的依赖。
提取连杆 (link)、关节 (joint)、几何体 (geometry)、运动学树。

对应功能 DT-01（3D 姿态同步）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from xml.etree import ElementTree as ET


class JointType(str, Enum):
    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"
    FIXED = "fixed"
    CONTINUOUS = "continuous"
    FLOATING = "floating"
    PLANAR = "planar"


class GeometryType(str, Enum):
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    MESH = "mesh"


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def zero(cls) -> Vector3:
        return cls(0.0, 0.0, 0.0)


@dataclass
class Pose:
    """URDF 原点姿态 (xyz + rpy)"""
    xyz: Vector3 = field(default_factory=Vector3.zero)
    rpy: Vector3 = field(default_factory=Vector3.zero)

    @property
    def translation(self) -> tuple[float, float, float]:
        return (self.xyz.x, self.xyz.y, self.xyz.z)

    @property
    def rotation_rpy(self) -> tuple[float, float, float]:
        return (self.rpy.x, self.rpy.y, self.rpy.z)


@dataclass
class Axis:
    """关节轴 (xyz)"""
    x: float = 0.0
    y: float = 0.0
    z: float = 1.0

    @classmethod
    def from_xyz(cls, x: float, y: float, z: float) -> Axis:
        # 归一化
        length = math.sqrt(x * x + y * y + z * z)
        if length < 1e-9:
            return cls(0, 0, 1)
        return cls(x / length, y / length, z / length)


@dataclass
class JointLimits:
    """关节限位"""
    lower: float = 0.0
    upper: float = 0.0
    effort: float = 100.0      # 最大力矩/力 (N·m / N)
    velocity: float = 10.0     # 最大速度 (rad/s / m/s)


@dataclass
class GeometryDef:
    """几何体定义"""
    geom_type: GeometryType = GeometryType.BOX
    origin: Pose = field(default_factory=Pose)
    # box: [x, y, z], sphere: [radius], cylinder: [radius, length], mesh: [filename, scale_x, scale_y, scale_z]
    parameters: list[float] = field(default_factory=list)
    mesh_filename: str = ""


@dataclass
class MaterialDef:
    """材质定义"""
    name: str = ""
    color_rgba: tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0)
    texture: str = ""


@dataclass
class LinkDef:
    """连杆定义"""
    name: str = ""
    visual: Optional[GeometryDef] = None
    collision: Optional[GeometryDef] = None
    inertial_mass: float = 0.0
    inertial_origin: Pose = field(default_factory=Pose)
    inertial_ixx: float = 0.0
    inertial_iyy: float = 0.0
    inertial_izz: float = 0.0


@dataclass
class JointDef:
    """关节定义"""
    name: str = ""
    joint_type: JointType = JointType.REVOLUTE
    parent: str = ""
    child: str = ""
    origin: Pose = field(default_factory=Pose)
    axis: Axis = field(default_factory=Axis)
    limits: JointLimits = field(default_factory=JointLimits)


@dataclass
class URDFModel:
    """URDF 模型

    包含完整的机器人运动学结构。
    """
    name: str = ""
    links: dict[str, LinkDef] = field(default_factory=dict)
    joints: list[JointDef] = field(default_factory=list)
    materials: dict[str, MaterialDef] = field(default_factory=dict)
    # 运动学树
    joint_map: dict[str, JointDef] = field(default_factory=dict)     # joint_name -> JointDef
    child_to_parent: dict[str, str] = field(default_factory=dict)    # child_link -> parent_link
    parent_to_joint: dict[str, JointDef] = field(default_factory=dict)  # child_link -> JointDef
    root_link: str = ""
    link_order_bfs: list[str] = field(default_factory=list)          # BFS 遍历顺序

    def get_joint_index(self, joint_name: str) -> int:
        """获取关节在可驱动关节列表中的索引"""
        for i, j in enumerate(self.joints):
            if j.name == joint_name:
                return i
        return -1

    @property
    def active_joints(self) -> list[JointDef]:
        """可驱动关节（非 fixed 类型）"""
        return [j for j in self.joints if j.joint_type != JointType.FIXED]

    @property
    def joint_names(self) -> list[str]:
        return [j.name for j in self.active_joints]


class URDFLoader:
    """URDF 文件/字符串解析器

    解析 URDF XML 文档，构建完整的 URDFModel。
    支持常用的 URDF 元素和属性。
    """

    @classmethod
    def from_file(cls, filepath: str) -> URDFModel:
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_string(f.read())

    @classmethod
    def from_string(cls, xml_str: str) -> URDFModel:
        root = ET.fromstring(xml_str)
        if root.tag != "robot":
            raise ValueError(f"Root element must be <robot>, got <{root.tag}>")

        model = URDFModel(name=root.get("name", "unnamed"))

        # 解析材质
        models = model
        for mat_elem in root.findall("material"):
            mat = cls._parse_material(mat_elem)
            if mat:
                models.materials[mat.name] = mat

        # 解析连杆
        for link_elem in root.findall("link"):
            link = cls._parse_link(link_elem)
            models.links[link.name] = link

        # 解析关节
        for joint_elem in root.findall("joint"):
            joint = cls._parse_joint(joint_elem)
            models.joints.append(joint)
            models.joint_map[joint.name] = joint
            models.child_to_parent[joint.child] = joint.parent
            models.parent_to_joint[joint.child] = joint

        # 建立运动学树根
        cls._build_kinematics_tree(models)

        return models

    @classmethod
    def _build_kinematics_tree(cls, model: URDFModel) -> None:
        """建立运动学树：找根连杆 + BFS排序"""
        child_links = set(model.child_to_parent.keys())
        all_links = set(model.links.keys())

        # 根连杆：未被任何关节作为子连杆的连杆
        root_candidates = all_links - child_links
        if root_candidates:
            model.root_link = next(iter(root_candidates))
        elif all_links:
            model.root_link = list(all_links)[0]

        # BFS 遍历
        if model.root_link:
            model.link_order_bfs = cls._bfs_order(model, model.root_link)
        else:
            model.link_order_bfs = list(all_links)

    @classmethod
    def _bfs_order(cls, model: URDFModel, start: str) -> list[str]:
        """BFS 遍历运动学树"""
        order = [start]
        queue = [start]
        # 构建 parent -> children 映射
        children: dict[str, list[str]] = {}
        for child, parent in model.child_to_parent.items():
            children.setdefault(parent, []).append(child)

        while queue:
            current = queue.pop(0)
            for child in children.get(current, []):
                order.append(child)
                queue.append(child)
        return order

    @classmethod
    def _parse_origin(cls, elem) -> Pose:
        xyz_str = elem.get("xyz", "0 0 0")
        rpy_str = elem.get("rpy", "0 0 0")
        xyz_parts = [float(v) for v in xyz_str.split()]
        rpy_parts = [float(v) for v in rpy_str.split()]
        while len(xyz_parts) < 3:
            xyz_parts.append(0.0)
        while len(rpy_parts) < 3:
            rpy_parts.append(0.0)
        return Pose(
            xyz=Vector3(xyz_parts[0], xyz_parts[1], xyz_parts[2]),
            rpy=Vector3(rpy_parts[0], rpy_parts[1], rpy_parts[2]),
        )

    @classmethod
    def _parse_axis(cls, elem) -> Axis:
        xyz_str = elem.get("xyz", "0 0 1")
        parts = [float(v) for v in xyz_str.split()]
        while len(parts) < 3:
            parts.append(0.0)
        return Axis.from_xyz(parts[0], parts[1], parts[2])

    @classmethod
    def _parse_limits(cls, elem) -> JointLimits:
        return JointLimits(
            lower=float(elem.get("lower", 0)),
            upper=float(elem.get("upper", 0)),
            effort=float(elem.get("effort", 100)),
            velocity=float(elem.get("velocity", 10)),
        )

    @classmethod
    def _parse_geometry(cls, elem) -> Optional[GeometryDef]:
        for child in elem:
            tag = child.tag
            if tag in ("box", "sphere", "cylinder", "mesh"):
                geom_type = GeometryType(tag)
                params = []
                mesh_fn = ""
                if tag == "box":
                    size_str = child.get("size", "0.1 0.1 0.1")
                    params = [float(v) for v in size_str.split()]
                elif tag == "sphere":
                    params = [float(child.get("radius", 0.1))]
                elif tag == "cylinder":
                    params = [
                        float(child.get("radius", 0.1)),
                        float(child.get("length", 0.2)),
                    ]
                elif tag == "mesh":
                    mesh_fn = child.get("filename", "")
                    scale_str = child.get("scale", "1 1 1")
                    params = [float(v) for v in scale_str.split()]

                origin_elem = next((e for e in elem if e.tag == "origin"), None)
                origin = cls._parse_origin(origin_elem) if origin_elem is not None else Pose()

                return GeometryDef(
                    geom_type=geom_type,
                    origin=origin,
                    parameters=params,
                    mesh_filename=mesh_fn,
                )
        return None

    @classmethod
    def _parse_link(cls, elem) -> LinkDef:
        name = elem.get("name", "unnamed_link")
        link = LinkDef(name=name)

        for child in elem:
            tag = child.tag
            if tag == "visual":
                geom_elem = child.find("geometry")
                if geom_elem is not None:
                    link.visual = cls._parse_geometry(geom_elem)
            elif tag == "collision":
                geom_elem = child.find("geometry")
                if geom_elem is not None:
                    link.collision = cls._parse_geometry(geom_elem)
            elif tag == "inertial":
                mass_elem = child.find("mass")
                if mass_elem is not None:
                    link.inertial_mass = float(mass_elem.get("value", 0))
                origin_elem = child.find("origin")
                if origin_elem is not None:
                    link.inertial_origin = cls._parse_origin(origin_elem)
                inertia_elem = child.find("inertia")
                if inertia_elem is not None:
                    link.inertial_ixx = float(inertia_elem.get("ixx", 0))
                    link.inertial_iyy = float(inertia_elem.get("iyy", 0))
                    link.inertial_izz = float(inertia_elem.get("izz", 0))

        return link

    @classmethod
    def _parse_joint(cls, elem) -> JointDef:
        name = elem.get("name", "unnamed_joint")
        joint_type_str = elem.get("type", "revolute")
        parent_elem = elem.find("parent")
        parent_link = parent_elem.get("link", "") if parent_elem is not None else ""
        child_elem = elem.find("child")
        child_link = child_elem.get("link", "") if child_elem is not None else ""
        joint = JointDef(
            name=name,
            joint_type=JointType(joint_type_str),
            parent=parent_link.strip(),
            child=child_link.strip(),
        )

        origin_elem = elem.find("origin")
        if origin_elem is not None:
            joint.origin = cls._parse_origin(origin_elem)

        axis_elem = elem.find("axis")
        if axis_elem is not None:
            joint.axis = cls._parse_axis(axis_elem)

        limit_elem = elem.find("limit")
        if limit_elem is not None:
            joint.limits = cls._parse_limits(limit_elem)

        return joint

    @classmethod
    def _parse_material(cls, elem) -> Optional[MaterialDef]:
        name = elem.get("name", "")
        if not name:
            return None
        color_elem = elem.find("color")
        rgba: tuple[float, float, float, float] = (0.7, 0.7, 0.7, 1.0)
        if color_elem is not None:
            rgba_str = color_elem.get("rgba", "0.7 0.7 0.7 1.0")
            parts = [float(v) for v in rgba_str.split()]
            if len(parts) == 4:
                rgba = (parts[0], parts[1], parts[2], parts[3])
        return MaterialDef(name=name, color_rgba=rgba)
