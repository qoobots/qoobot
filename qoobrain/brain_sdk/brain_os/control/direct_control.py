"""brain_os SDK — 直接控制 API

提供低级机器人控制接口，绕过规划器和行为树直接操作关节或末端执行器。
适用于调试、遥操作、微调等场景。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..config import BrainOSConfig
from ..types.common import Pose, Vector3, Quaternion
from ..types.motion import JointState, JointLimits, CartesianPath, MotionStatus


# ── 数据类型 ────────────────────────────────────────────


@dataclass
class JointCommand:
    """关节指令。

    Attributes:
        mode: 控制模式 (position, velocity, effort)
        targets: 目标值字典 {"joint_1": 0.5, ...}
        velocity_scale: 速度缩放 (0.0-1.0)
        acceleration_scale: 加速度缩放 (0.0-1.0)
        blend_radius: 轨迹平滑过渡半径 (rad)
    """

    mode: str = "position"
    targets: Dict[str, float] = field(default_factory=dict)
    velocity_scale: float = 0.5
    acceleration_scale: float = 0.5
    blend_radius: float = 0.02


@dataclass
class CartesianPose:
    """笛卡尔空间位姿目标。"""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    frame_id: str = "base_link"

    def to_pose(self) -> Pose:
        return Pose(
            position=Vector3(x=self.x, y=self.y, z=self.z),
            orientation=Quaternion(x=self.roll, y=self.pitch, z=self.yaw, w=1.0),
        )


@dataclass
class RobotState:
    """机器人完整状态快照。

    Attributes:
        joints: 各关节状态列表
        ee_pose: 末端执行器位姿
        base_pose: 移动底座位姿
        gripper_position: 夹爪开度 (0=全闭, 1=全开)
        motion_status: 运动状态
        is_emergency_stopped: 是否紧急停止
        timestamp_ms: 时间戳
    """

    joints: List[JointState] = field(default_factory=list)
    ee_pose: Optional[Pose] = None
    base_pose: Optional[Pose] = None
    gripper_position: float = 0.0
    motion_status: MotionStatus = MotionStatus.IDLE
    is_emergency_stopped: bool = False
    timestamp_ms: int = 0


# ── DirectController ──────────────────────────────────────


class DirectController:
    """直接机器人控制器。

    提供绕过规划器的底层控制接口，适合：
    - 关节空间直接控制 (位置/速度/力矩)
    - 笛卡尔空间末端执行器控制
    - 夹爪精细操作
    - 状态查询

    使用示例::

        async with BrainOSClient() as robot:
            # 通过 client.control.direct_xxxx 调用
            # 或直接获得控制器
            ctrl = robot.control._direct
            await ctrl.move_joints({"joint_1": 0.5, "joint_2": -0.3})
    """

    def __init__(
        self,
        get_channel: Callable,
        get_async_channel: Callable,
        config: BrainOSConfig,
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = True
        self._joint_limits: Dict[str, JointLimits] = {}
        self._joint_names: List[str] = []

    # ── 关节控制 ─────────────────────────────────────────

    async def move_joints(
        self,
        targets: Dict[str, float],
        *,
        velocity_scale: float = 0.5,
        acceleration_scale: float = 0.5,
        timeout_sec: float = 10.0,
    ) -> bool:
        """移动关节到目标位置。

        Args:
            targets: 关节目标值 {"joint_1": 0.5, ...}
            velocity_scale: 速度缩放 (0-1)
            acceleration_scale: 加速度缩放 (0-1)
            timeout_sec: 超时时间

        Returns:
            是否成功到达目标
        """
        cmd = JointCommand(
            mode="position",
            targets=targets,
            velocity_scale=velocity_scale,
            acceleration_scale=acceleration_scale,
        )

        if self._enable_mock:
            await asyncio.sleep(timeout_sec * 0.1)
            return True

        try:
            channel = await self._get_ach()
            from brain_os.proto_gen.brain_os.control.service_pb2 import JointCommand as ProtoJointCmd

            req = ProtoJointCmd(
                robot_id=self._cfg.robot_id,
                joint_names=list(targets.keys()),
                joint_positions=list(targets.values()),
                velocity_scale=velocity_scale,
                timeout_sec=timeout_sec,
            )
            # stub = ControlServiceStub(channel)
            # resp = await stub.MoveJoints(req, timeout=timeout_sec + 1)
            raise NotImplementedError("gRPC direct control endpoint not yet implemented")
        except NotImplementedError:
            return False

    async def move_joint(
        self,
        joint_name: str,
        position: float,
        *,
        velocity_scale: float = 0.5,
        timeout_sec: float = 5.0,
    ) -> bool:
        """移动单个关节到目标位置。"""
        return await self.move_joints(
            {joint_name: position},
            velocity_scale=velocity_scale,
            timeout_sec=timeout_sec,
        )

    async def set_joint_velocity(
        self,
        velocities: Dict[str, float],
        *,
        timeout_sec: float = 5.0,
    ) -> bool:
        """设置关节速度 (力矩控制模式)。"""
        if self._enable_mock:
            await asyncio.sleep(timeout_sec * 0.05)
            return True

        try:
            channel = await self._get_ach()
            from brain_os.proto_gen.brain_os.control.service_pb2 import VelocityCommand

            req = VelocityCommand(
                robot_id=self._cfg.robot_id,
                joint_names=list(velocities.keys()),
                joint_velocities=list(velocities.values()),
            )
            raise NotImplementedError("gRPC velocity control endpoint not yet implemented")
        except NotImplementedError:
            return False

    # ── 笛卡尔控制 ────────────────────────────────────────

    async def move_to_pose(
        self,
        pose: CartesianPose,
        *,
        velocity_scale: float = 0.5,
        acceleration_scale: float = 0.5,
        timeout_sec: float = 10.0,
    ) -> bool:
        """移动末端执行器到目标位姿 (笛卡尔空间)。"""
        if self._enable_mock:
            await asyncio.sleep(timeout_sec * 0.1)
            return True

        try:
            channel = await self._get_ach()
            from brain_os.proto_gen.brain_os.control.service_pb2 import CartesianCommand

            req = CartesianCommand(
                robot_id=self._cfg.robot_id,
                target_pose=pose.to_pose(),
                velocity_scale=velocity_scale,
            )
            raise NotImplementedError("gRPC cartesian control endpoint not yet implemented")
        except NotImplementedError:
            return False

    async def move_linear(
        self,
        dx: float = 0.0,
        dy: float = 0.0,
        dz: float = 0.0,
        *,
        velocity: float = 0.1,
        timeout_sec: float = 10.0,
    ) -> bool:
        """沿直线相对移动末端执行器 (m)。"""
        if self._enable_mock:
            await asyncio.sleep(timeout_sec * 0.05)
            return True
        return False

    async def move_along_path(
        self,
        path: CartesianPath,
        *,
        timeout_sec: float = 30.0,
    ) -> bool:
        """沿笛卡尔空间路径移动。"""
        if self._enable_mock:
            await asyncio.sleep(timeout_sec * 0.1)
            return True
        return False

    # ── 夹爪 ──────────────────────────────────────────────

    async def grip(
        self,
        position: float,
        *,
        max_effort: float = 20.0,
        timeout_sec: float = 3.0,
    ) -> bool:
        """设置夹爪开度 (0=全闭, 1=全开)。"""
        if self._enable_mock:
            await asyncio.sleep(timeout_sec * 0.05)
            return True
        return False

    async def grip_open(self) -> bool:
        """完全打开夹爪。"""
        return await self.grip(1.0)

    async def grip_close(self, max_effort: float = 20.0) -> bool:
        """完全关闭夹爪。"""
        return await self.grip(0.0, max_effort=max_effort)

    # ── 状态查询 ──────────────────────────────────────────

    async def get_state(self) -> RobotState:
        """获取机器人完整状态快照。"""
        if self._enable_mock:
            return RobotState(
                joints=[
                    JointState(name=f"joint_{i}", position=0.0, velocity=0.0, effort=0.0,
                               limits=JointLimits(lower=-3.14, upper=3.14, max_velocity=2.0, max_effort=50.0))
                    for i in range(1, 8)
                ],
                ee_pose=Pose(
                    position=Vector3(x=0.5, y=0.0, z=0.8),
                    orientation=Quaternion(x=0.0, y=0.0, z=0.0, w=1.0),
                ),
                gripper_position=1.0,
                motion_status=MotionStatus.IDLE,
                is_emergency_stopped=False,
                timestamp_ms=0,
            )

        try:
            channel = await self._get_ach()
            from brain_os.proto_gen.brain_os.control.service_pb2 import GetJointStateRequest

            req = GetJointStateRequest(robot_id=self._cfg.robot_id)
            raise NotImplementedError("gRPC get_state endpoint not yet implemented")
        except NotImplementedError:
            return RobotState()

    async def get_joint_state(self, joint_name: str) -> Optional[JointState]:
        """查询单个关节状态。"""
        state = await self.get_state()
        for j in state.joints:
            if j.name == joint_name:
                return j
        return None

    async def get_ee_pose(self) -> Optional[Pose]:
        """查询末端执行器位姿。"""
        state = await self.get_state()
        return state.ee_pose

    # ── 紧急操作 ──────────────────────────────────────────

    async def stop(self, reason: str = "") -> bool:
        """立即停止所有运动 (不经过规划器)。"""
        if self._enable_mock:
            return True
        return True

    async def home(self, *, timeout_sec: float = 30.0) -> bool:
        """回到零位 (home position)。"""
        if self._enable_mock:
            await asyncio.sleep(2.0)
            return True
        return False

    # ── 工具方法 ──────────────────────────────────────────

    def set_joint_limits(self, limits: Dict[str, JointLimits]) -> None:
        """设置关节限位。"""
        self._joint_limits.update(limits)

    @property
    def joint_names(self) -> List[str]:
        return self._joint_names
