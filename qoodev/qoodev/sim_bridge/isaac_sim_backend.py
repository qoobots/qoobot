"""Isaac Sim 仿真后端。

基于 NVIDIA Isaac Sim 的仿真后端实现。
支持 USD 场景格式，提供最高物理精度和 GPU 加速。

Requirements:
    - NVIDIA Isaac Sim 已安装
    - isaacsim Python 环境
"""

import logging
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np

from .interface import (
    SimBackend,
    SimConfig,
    SimControlCommand,
    SimScene,
    SimSensorData,
    SimState,
    SimStats,
    SensorType,
    ControlMode,
)

logger = logging.getLogger(__name__)


class IsaacSimBackend(SimBackend):
    """NVIDIA Isaac Sim 后端。

    注意：Isaac Sim 需要 NVIDIA GPU 和特定的 Python 环境。
    此实现提供接口桩，实际功能在 Isaac Sim 环境中运行。
    """

    def __init__(self, config: SimConfig):
        super().__init__(config)
        self._world = None           # omni.isaac.core.World
        self._scene = None           # omni.isaac.core.scenes.Scene
        self._robots: dict[str, Any] = {}     # name -> robot instance
        self._camera_sensors: dict[str, Any] = {}
        self._is_standalone = False  # 是否为独立模式（无 Isaac Sim）

    # ── 生命周期 ──────────────────────────────────────

    def initialize(self) -> None:
        """初始化 Isaac Sim 引擎。"""
        try:
            from omni.isaac.kit import SimulationApp
            self._is_standalone = False
            logger.info("Isaac Sim 环境已连接")
        except ImportError:
            logger.warning(
                "Isaac Sim 未安装。运行在桩模式（stub mode），"
                "部分功能不可用。请安装 Isaac Sim 以获得完整功能。"
            )
            self._is_standalone = True

        if not self._is_standalone:
            self._init_isaac_world()

        self.state = SimState.READY
        logger.info("Isaac Sim 后端初始化完成" +
                    ("（桩模式）" if self._is_standalone else ""))

    def load_scene(self, scene: SimScene) -> None:
        """加载 USD 场景。"""
        self.state = SimState.LOADING
        self.scene = scene

        if self._is_standalone:
            logger.info(f"[桩模式] 加载场景: {scene.name}")
            self.state = SimState.READY
            return

        # 加载 USD 场景
        from omni.isaac.core.utils.stage import add_reference_to_stage
        from omni.isaac.core.utils.prims import get_prim_at_path

        if scene.scene_path:
            add_reference_to_stage(
                usd_path=scene.scene_path,
                prim_path="/World/scene"
            )
            logger.info(f"加载 USD 场景: {scene.scene_path}")

        # 加载机器人
        for robot in scene.robots:
            self._add_robot(robot)

        # 加载物体
        for obj in scene.objects:
            self._add_object(obj)

        # 设置灯光
        for light in scene.lights:
            self._add_light(light)

        self._world.reset()
        self.state = SimState.READY
        logger.info(f"场景加载完成: {scene.name}")

    def step(self) -> None:
        """推进仿真。"""
        if self.state != SimState.RUNNING:
            return

        step_start = time.perf_counter()

        if not self._is_standalone:
            self._world.step(render=not self.config.headless)
            physics_time = time.perf_counter() - step_start
        else:
            time.sleep(self.config.time_step)
            physics_time = self.config.time_step

        self.stats.total_steps += 1
        self.stats.total_time += self.config.time_step
        self.stats.physics_time_ms = physics_time * 1000
        self.stats.step_time_ms = physics_time * 1000

    def reset(self) -> None:
        """重置仿真。"""
        if not self._is_standalone:
            self._world.reset()
        self.stats = SimStats()
        logger.info("仿真已重置")

    def shutdown(self) -> None:
        """关闭 Isaac Sim。"""
        self.state = SimState.STOPPED
        if not self._is_standalone:
            self._world.stop()
            self._world.clear_instance()
        self._robots.clear()
        self._camera_sensors.clear()
        logger.info("Isaac Sim 后端已关闭")

    # ── 状态控制 ──────────────────────────────────────

    def pause(self) -> None:
        if self.state == SimState.RUNNING:
            self.state = SimState.PAUSED
            if not self._is_standalone:
                self._world.pause()

    def resume(self) -> None:
        if self.state == SimState.PAUSED:
            self.state = SimState.RUNNING
            if not self._is_standalone:
                self._world.play()

    # ── 传感器 ────────────────────────────────────────

    def get_sensor_data(self, sensor_name: str) -> SimSensorData:
        """获取传感器数据。"""
        if self._is_standalone:
            return self._stub_sensor_data(sensor_name)

        if sensor_name in self._camera_sensors:
            return self._get_camera_data(sensor_name)
        else:
            return self._get_robot_sensor_data(sensor_name)

    def get_all_sensor_data(self) -> list[SimSensorData]:
        """获取所有传感器数据。"""
        if self._is_standalone:
            return [self._stub_sensor_data("stub_sensor")]

        results = []
        for name in self._camera_sensors:
            results.append(self._get_camera_data(name))
        for robot_name, robot in self._robots.items():
            try:
                results.append(self._get_robot_sensor_data(robot_name))
            except Exception:
                logger.exception(f"读取机器人 {robot_name} 传感器失败")
        return results

    # ── 控制 ──────────────────────────────────────────

    def apply_control(self, command: SimControlCommand) -> None:
        """发送控制指令。"""
        if self._is_standalone:
            logger.debug(f"[桩模式] 控制指令: {command.robot_name} "
                         f"{command.control_mode.value} "
                         f"targets={command.targets[:3]}")
            return

        robot = self._robots.get(command.robot_name)
        if robot is None:
            logger.warning(f"机器人不存在: {command.robot_name}")
            return

        # 通过 Articulation API 控制
        from omni.isaac.core.utils.types import ArticulationAction
        action = ArticulationAction(joint_positions=command.targets)
        robot.apply_action(action)

    def get_joint_states(self, robot_name: str) -> dict[str, Any]:
        """获取关节状态。"""
        if self._is_standalone:
            return {
                "name": robot_name,
                "positions": {},
                "velocities": {},
                "timestamp": time.time(),
            }

        robot = self._robots.get(robot_name)
        if robot is None:
            return {"name": robot_name, "positions": {}, "velocities": {}}

        joints = robot.get_joint_positions()
        velocities = robot.get_joint_velocities()
        return {
            "name": robot_name,
            "positions": {f"joint_{i}": float(j) for i, j in enumerate(joints)},
            "velocities": {f"joint_{i}": float(v) for i, v in enumerate(velocities)},
            "timestamp": self._world.current_time,
        }

    # ── 位姿查询 ──────────────────────────────────────

    def get_robot_pose(self, robot_name: str) -> tuple[np.ndarray, np.ndarray]:
        """获取机器人基座位姿。"""
        if self._is_standalone:
            return np.zeros(3), np.array([1.0, 0.0, 0.0, 0.0])

        robot = self._robots.get(robot_name)
        if robot is None:
            return np.zeros(3), np.array([1.0, 0.0, 0.0, 0.0])

        pos, rot = robot.get_world_pose()
        return pos, rot

    def get_object_pose(self, object_name: str) -> tuple[np.ndarray, np.ndarray]:
        """获取物体位姿。"""
        if self._is_standalone:
            return np.zeros(3), np.array([1.0, 0.0, 0.0, 0.0])

        # 通过 prim 路径获取
        try:
            from omni.usd import get_context
            from pxr import UsdGeom
            stage = get_context().get_stage()
            prim_path = f"/World/objects/{object_name}"
            prim = stage.GetPrimAtPath(prim_path)
            if prim.IsValid():
                xform = UsdGeom.Xformable(prim)
                transform = xform.GetLocalTransformation()
                pos = np.array([transform.ExtractTranslation()])
                return pos.flatten(), np.array([1.0, 0.0, 0.0, 0.0])
        except Exception:
            pass
        return np.zeros(3), np.array([1.0, 0.0, 0.0, 0.0])

    # ── 渲染 ──────────────────────────────────────────

    def render(self, camera_name: str = "") -> np.ndarray:
        """渲染一帧图像。"""
        if self._is_standalone:
            return np.zeros((self.config.render_height, self.config.render_width, 3),
                          dtype=np.uint8)

        if camera_name and camera_name in self._camera_sensors:
            return self._camera_sensors[camera_name].get_rgba()[:, :, :3]

        # 默认渲染
        return np.zeros((self.config.render_height, self.config.render_width, 3),
                       dtype=np.uint8)

    # ── 统计 ──────────────────────────────────────────

    def get_stats(self) -> SimStats:
        if not self._is_standalone and self._world:
            self.stats.real_time_factor = self._world.get_physics_dt() / (
                self.config.time_step or 0.001
            )
        return self.stats

    # ── 内部方法 ───────────────────────────────────────

    def _init_isaac_world(self) -> None:
        """初始化 Isaac Sim World。"""
        from omni.isaac.core import World
        self._world = World(
            physics_dt=self.config.time_step,
            rendering_dt=self.config.time_step,
        )

    def _add_robot(self, robot) -> None:
        """加载机器人到场景。"""
        if self._is_standalone:
            return

        from omni.isaac.core.utils.stage import add_reference_to_stage
        from omni.isaac.core.robots import Robot

        robot_path = f"/World/robots/{robot.name}"
        if robot.model_path:
            add_reference_to_stage(
                usd_path=robot.model_path,
                prim_path=robot_path,
            )

        isaac_robot = Robot(prim_path=robot_path, name=robot.name)
        self._world.scene.add(isaac_robot)
        self._robots[robot.name] = isaac_robot
        logger.info(f"机器人已加载: {robot.name}")

    def _add_object(self, obj: dict) -> None:
        """加载物体到场景。"""
        if self._is_standalone:
            return

        from omni.isaac.core.utils.stage import add_reference_to_stage

        obj_path = f"/World/objects/{obj['name']}"
        if obj.get("path"):
            add_reference_to_stage(usd_path=obj["path"], prim_path=obj_path)

    def _add_light(self, light: dict) -> None:
        """添加灯光到场景。"""
        if self._is_standalone:
            return
        # Isaac Sim 默认灯光通常足够，此处可扩展
        pass

    def _get_camera_data(self, name: str) -> SimSensorData:
        """获取相机传感器数据。"""
        cam = self._camera_sensors.get(name)
        if cam is None:
            raise KeyError(f"相机不存在: {name}")

        rgba = cam.get_rgba()
        return SimSensorData(
            sensor_type=SensorType.RGBD_CAMERA,
            timestamp=self._world.current_time,
            data=rgba[:, :, :3],  # RGB
            frame_id=name,
            metadata={"depth": rgba[:, :, 3]},
        )

    def _get_robot_sensor_data(self, robot_name: str) -> SimSensorData:
        """获取机器人传感器数据。"""
        states = self.get_joint_states(robot_name)
        return SimSensorData(
            sensor_type=SensorType.JOINT_STATES,
            timestamp=states["timestamp"],
            data={
                "positions": states["positions"],
                "velocities": states["velocities"],
            },
            frame_id=robot_name,
        )

    def _stub_sensor_data(self, name: str) -> SimSensorData:
        """生成桩传感器数据（用于无 Isaac Sim 环境）。"""
        return SimSensorData(
            sensor_type=SensorType.JOINT_STATES,
            timestamp=time.time(),
            data={"positions": {}, "velocities": {}},
            frame_id=name,
            metadata={"stub": True},
        )
