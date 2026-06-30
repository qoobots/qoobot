"""骨架姿态驱动 — 关节角度到连杆位姿的正向运动学

接收关节角度向量，通过 URDF 运动学树计算每个连杆的世界位姿。
支持关节限位夹紧、位置/速度限制。

对应功能 DT-01（3D 姿态同步）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from console.core.twins.urdf_loader import (
    URDFModel, JointDef, JointType, LinkDef, Pose, Vector3, Axis,
)


@dataclass
class Quaternion:
    """四元数 (w, x, y, z)"""
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def identity(cls) -> Quaternion:
        return cls(1.0, 0.0, 0.0, 0.0)

    @classmethod
    def from_axis_angle(cls, ax: float, ay: float, az: float, angle_rad: float) -> Quaternion:
        """从轴+角度构造四元数"""
        half = angle_rad * 0.5
        s = math.sin(half)
        return cls(math.cos(half), ax * s, ay * s, az * s)

    @classmethod
    def from_rpy(cls, roll: float, pitch: float, yaw: float) -> Quaternion:
        """从 RPY (弧度) 构造四元数"""
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        return cls(
            w=cr * cp * cy + sr * sp * sy,
            x=sr * cp * cy - cr * sp * sy,
            y=cr * sp * cy + sr * cp * sy,
            z=cr * cp * sy - sr * sp * cy,
        )

    def multiply(self, other: Quaternion) -> Quaternion:
        """四元数乘法 (self * other)"""
        return Quaternion(
            w=self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
            x=self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            y=self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            z=self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
        )

    def conjugate(self) -> Quaternion:
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def rotate_vector(self, v: tuple[float, float, float]) -> tuple[float, float, float]:
        """用此四元数旋转三维向量"""
        qv = Quaternion(0, v[0], v[1], v[2])
        qr = self.multiply(qv).multiply(self.conjugate())
        return (qr.x, qr.y, qr.z)


@dataclass
class Transform:
    """空间变换 (平移 + 旋转)"""
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Quaternion = field(default_factory=Quaternion.identity)

    @classmethod
    def identity(cls) -> Transform:
        return cls()

    @classmethod
    def from_pose(cls, pose: Pose) -> Transform:
        """从 URDF Pose 构造 Transform"""
        return cls(
            translation=(pose.xyz.x, pose.xyz.y, pose.xyz.z),
            rotation=Quaternion.from_rpy(pose.rpy.x, pose.rpy.y, pose.rpy.z),
        )

    def compose(self, other: Transform) -> Transform:
        """组合变换: self ∘ other (先other再self)"""
        # 旋转叠加
        new_rot = self.rotation.multiply(other.rotation)
        # 平移叠加: t_self + R_self * t_other
        rc = self.rotation.rotate_vector(other.translation)
        new_trans = (
            self.translation[0] + rc[0],
            self.translation[1] + rc[1],
            self.translation[2] + rc[2],
        )
        return Transform(new_trans, new_rot)

    def to_matrix_4x4(self) -> list[list[float]]:
        """返回 4x4 齐次变换矩阵 (行主序)"""
        q = self.rotation
        qw, qx, qy, qz = q.w, q.x, q.y, q.z
        tx, ty, tz = self.translation

        return [
            [1 - 2*qy*qy - 2*qz*qz,     2*qx*qy - 2*qz*qw,     2*qx*qz + 2*qy*qw, tx],
            [    2*qx*qy + 2*qz*qw, 1 - 2*qx*qx - 2*qz*qz,     2*qy*qz - 2*qx*qw, ty],
            [    2*qx*qz - 2*qy*qw,     2*qy*qz + 2*qx*qw, 1 - 2*qx*qx - 2*qy*qy, tz],
            [                     0,                      0,                      0,  1],
        ]


@dataclass
class LinkPose:
    """连杆世界位姿"""
    link_name: str = ""
    transform: Transform = field(default_factory=Transform.identity)
    # 可视化几何的中心世界坐标
    visual_center: tuple[float, float, float] = (0.0, 0.0, 0.0)


class SkeletonDriver:
    """骨架姿态驱动

    给定 URDF 模型和关节角度向量，计算每个连杆的世界位姿。
    使用正向运动学链式传播。

    对应功能 DT-01（3D 姿态同步）。
    """

    def __init__(self, model: URDFModel) -> None:
        self._model = model
        self._joint_positions: dict[str, float] = {}    # joint_name -> angle_rad
        self._link_poses: dict[str, LinkPose] = {}       # link_name -> LinkPose

        # 初始默认位置（零位）
        for joint in model.active_joints:
            self._joint_positions[joint.name] = 0.0

        # 预计算固定变换（joint origin transforms）
        self._joint_origin_transforms: dict[str, Transform] = {}
        for joint in model.joints:
            self._joint_origin_transforms[joint.name] = Transform.from_pose(joint.origin)

    @property
    def model(self) -> URDFModel:
        return self._model

    @property
    def joint_positions(self) -> dict[str, float]:
        return dict(self._joint_positions)

    @property
    def link_poses(self) -> dict[str, LinkPose]:
        return dict(self._link_poses)

    def set_joint_position(self, joint_name: str, angle_rad: float) -> None:
        """设置单个关节角度（自动限位夹紧）"""
        joint = self._model.joint_map.get(joint_name)
        if joint and joint.joint_type != JointType.FIXED:
            lo, hi = joint.limits.lower, joint.limits.upper
            self._joint_positions[joint_name] = max(lo, min(hi, angle_rad))

    def set_joint_positions(self, positions: dict[str, float]) -> None:
        """批量设置关节角度"""
        for name, angle in positions.items():
            self.set_joint_position(name, angle)

    def compute_forward_kinematics(self) -> dict[str, LinkPose]:
        """计算正向运动学，返回所有连杆的世界位姿

        按 BFS 顺序从根连杆向外递推。
        """
        self._link_poses.clear()

        if not self._model.root_link:
            return {}

        # 根连杆（世界原点）
        root = self._model.root_link
        root_pose = LinkPose(
            link_name=root,
            transform=Transform.identity(),
            visual_center=(0.0, 0.0, 0.0),
        )
        self._link_poses[root] = root_pose

        # 按 BFS 顺序遍历
        for link_name in self._model.link_order_bfs:
            if link_name == root:
                continue

            parent_link = self._model.child_to_parent.get(link_name)
            if parent_link is None:
                continue

            joint = self._model.parent_to_joint.get(link_name)
            if joint is None:
                continue

            parent_pose = self._link_poses.get(parent_link)
            if parent_pose is None:
                continue

            # 关节原点变换
            T_joint = self._joint_origin_transforms.get(joint.name, Transform.identity())

            # 关节运动旋转变换
            angle = self._joint_positions.get(joint.name, 0.0)
            if joint.joint_type in (JointType.REVOLUTE, JointType.CONTINUOUS):
                ax = joint.axis
                T_rot = Transform(
                    rotation=Quaternion.from_axis_angle(ax.x, ax.y, ax.z, angle),
                )
            elif joint.joint_type == JointType.PRISMATIC:
                ax = joint.axis
                T_rot = Transform(
                    translation=(ax.x * angle, ax.y * angle, ax.z * angle),
                )
            else:
                T_rot = Transform.identity()

            # 子连杆的世界变换 = parent_pose * T_joint * T_rot
            link_transform = parent_pose.transform.compose(T_joint).compose(T_rot)

            # 可视化几何中心（如果有视觉几何体的话）
            link_def = self._model.links.get(link_name)
            vc: tuple[float, float, float] = (0.0, 0.0, 0.0)
            if link_def and link_def.visual:
                vis_origin = link_def.visual.origin
                T_vis = Transform.from_pose(vis_origin)
                vis_transform = link_transform.compose(T_vis)
                vc = vis_transform.translation
            else:
                vc = link_transform.translation

            self._link_poses[link_name] = LinkPose(
                link_name=link_name,
                transform=link_transform,
                visual_center=vc,
            )

        return self._link_poses

    def get_joint_axis_world(self, joint_name: str) -> Optional[tuple[float, float, float]]:
        """获取关节轴在世界坐标系中的方向"""
        joint = self._model.joint_map.get(joint_name)
        if joint is None:
            return None
        parent_link = joint.parent
        parent_pose = self._link_poses.get(parent_link)
        if parent_pose is None:
            return None
        ax = joint.axis
        return parent_pose.transform.rotation.rotate_vector((ax.x, ax.y, ax.z))

    def get_link_chain(self, start_link: str, end_link: str) -> list[str]:
        """获取从 start_link 到 end_link 的连杆链"""
        # 构建 parent->children
        children: dict[str, list[str]] = {}
        for child, parent in self._model.child_to_parent.items():
            children.setdefault(parent, []).append(child)

        # BFS 从 start 找 end
        parent_of = {start_link: None}
        queue = [start_link]
        while queue:
            current = queue.pop(0)
            if current == end_link:
                break
            for child in children.get(current, []):
                if child not in parent_of:
                    parent_of[child] = current
                    queue.append(child)

        if end_link not in parent_of:
            return []

        # 回溯路径
        path = []
        current = end_link
        while current is not None:
            path.insert(0, current)
            current = parent_of.get(current)
        return path
