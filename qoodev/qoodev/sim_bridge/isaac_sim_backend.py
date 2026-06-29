"""Isaac Sim 仿真后端。

基于 NVIDIA Isaac Sim 的仿真后端实现。
支持 USD 场景格式，提供最高物理精度和 GPU 加速。

Requirements:
    - NVIDIA Isaac Sim 已安装
    - isaacsim Python 环境

当 Isaac Sim 不可用时，后端退化为功能性的桩模式（stub mode），
允许开发者在不具备 GPU 的环境中进行基本的代码流验证。
"""

import logging
import math
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

    在完整的 Isaac Sim 环境中提供最高物理精度和 GPU 加速的传感器仿真。
    当 Isaac Sim 不可用时，退化为桩模式：提供模拟的传感器数据和控制接口，
    支持基本的代码流测试和 CI/CD 验证。

    Attributes:
        _is_standalone: 是否运行在桩模式（无 Isaac Sim 环境）
        _stub_time: 桩模式下的仿真时间计数器
        _stub_joints: 桩模式下的模拟关节状态
    """

    def __init__(self, config: SimConfig):
        super().__init__(config)
        self._world = None           # omni.isaac.core.World
        self._scene = None           # omni.isaac.core.scenes.Scene
        self._robots: dict[str, Any] = {}     # name -> robot instance
        self._camera_sensors: dict[str, Any] = {}
        self._is_standalone = False  # 是否为独立模式（无 Isaac Sim）
        # Stub mode state
        self._stub_time: float = 0.0
        self._stub_joints: dict[str, dict[str, float]] = {}
        self._stub_sensors: dict[str, SimSensorData] = {}
        self._scene_config: Optional[SimScene] = None

    # ── 生命周期 ──────────────────────────────────────

    def initialize(self) -> None:
        """初始化 Isaac Sim 引擎。

        尝试连接 Isaac Sim Python API。如果未安装，退化为桩模式，
        仍可执行基本的仿真循环，但使用模拟数据。
        """
        try:
            from omni.isaac.kit import SimulationApp
            self._is_standalone = False
            logger.info("Isaac Sim 环境已连接")
        except ImportError:
            logger.warning(
                "Isaac Sim 未安装。运行在桩模式（stub mode）。\n"
                "  仿真循环正常运行，但传感器数据为模拟值。\n"
                "  安装 Isaac Sim 以获得完整物理仿真和 GPU 加速渲染。\n"
                "  参考: https://developer.nvidia.com/isaac-sim"
            )
            self._is_standalone = True

        if not self._is_standalone:
            self._init_isaac_world()

        self.state = SimState.READY
        mode_info = "（桩模式 - 模拟数据）" if self._is_standalone else ""
        logger.info(f"Isaac Sim 后端初始化完成 {mode_info}")

    def load_scene(self, scene: SimScene) -> None:
        """加载 USD 场景。

        在桩模式下，记录场景配置以便生成模拟传感器数据。
        在完整模式下，通过 USD API 加载场景文件。
        """
        self.state = SimState.LOADING
        self.scene = scene
        self._scene_config = scene

        if self._is_standalone:
            self._init_stub_scene(scene)
            self.state = SimState.READY
            logger.info(f"[桩模式] 场景就绪: {scene.name} "
                        f"(机器人: {len(scene.robots)}, 物体: {len(scene.objects)})")
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
        """推进仿真一步。

        在桩模式下，使用简化的运动学模型推进状态。
        在完整模式下，调用 Isaac Sim 物理引擎。
        """
        if self.state != SimState.RUNNING:
            return

        step_start = time.perf_counter()

        if self._is_standalone:
            self._stub_step()
            physics_time = self.config.time_step
        else:
            self._world.step(render=not self.config.headless)
            physics_time = time.perf_counter() - step_start

        self.stats.total_steps += 1
        self.stats.total_time += self.config.time_step
        self.stats.physics_time_ms = physics_time * 1000
        self.stats.step_time_ms = (time.perf_counter() - step_start) * 1000

    def reset(self) -> None:
        """重置仿真到初始状态。"""
        if self._is_standalone:
            self._stub_time = 0.0
            if self._scene_config:
                self._init_stub_scene(self._scene_config)
        else:
            self._world.reset()
        self.stats = SimStats()
        logger.info("仿真已重置")

    def shutdown(self) -> None:
        """关闭 Isaac Sim，释放 GPU 资源。"""
        self.state = SimState.STOPPED
        if not self._is_standalone:
            self._world.stop()
            self._world.clear_instance()
        self._robots.clear()
        self._camera_sensors.clear()
        self._stub_joints.clear()
        self._stub_sensors.clear()
        logger.info("Isaac Sim 后端已关闭")

    # ── 状态控制 ──────────────────────────────────────

    def pause(self) -> None:
        if self.state == SimState.RUNNING:
            self.state = SimState.PAUSED
            if not self._is_standalone:
                self._world.pause()
            logger.debug("仿真已暂停")

    def resume(self) -> None:
        if self.state == SimState.PAUSED:
            self.state = SimState.RUNNING
            if not self._is_standalone:
                self._world.play()
            logger.debug("仿真已恢复")

    # ── 传感器 ────────────────────────────────────────

    def get_sensor_data(self, sensor_name: str) -> SimSensorData:
        """获取指定传感器的最新数据。"""
        if self._is_standalone:
            return self._get_stub_sensor_data(sensor_name)

        if sensor_name in self._camera_sensors:
            return self._get_camera_data(sensor_name)
        else:
            return self._get_robot_sensor_data(sensor_name)

    def get_all_sensor_data(self) -> list[SimSensorData]:
        """获取所有传感器的最新数据。"""
        if self._is_standalone:
            return list(self._stub_sensors.values())

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
        """向指定机器人发送控制指令。"""
        if self._is_standalone:
            self._stub_apply_control(command)
            return

        robot = self._robots.get(command.robot_name)
        if robot is None:
            logger.warning(f"机器人不存在: {command.robot_name}")
            return

        # 通过 Articulation API 控制
        from omni.isaac.core.utils.types import ArticulationAction

        if command.control_mode == ControlMode.POSITION:
            action = ArticulationAction(joint_positions=command.targets)
        elif command.control_mode == ControlMode.VELOCITY:
            action = ArticulationAction(joint_velocities=command.targets)
        elif command.control_mode == ControlMode.TORQUE:
            action = ArticulationAction(joint_efforts=command.targets)
        else:
            action = ArticulationAction(joint_positions=command.targets)

        robot.apply_action(action)

    def get_joint_states(self, robot_name: str) -> dict[str, Any]:
        """获取机器人关节状态。"""
        if self._is_standalone:
            joints = self._stub_joints.get(robot_name, {})
            return {
                "name": robot_name,
                "positions": joints,
                "velocities": {k: 0.0 for k in joints},
                "timestamp": self._stub_time,
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
        """获取机器人基座位姿 (position, quaternion)。"""
        if self._is_standalone:
            # 模拟简单的圆周运动
            angle = self._stub_time * 0.5
            radius = 1.0
            pos = np.array([radius * math.cos(angle), radius * math.sin(angle), 0.0])
            quat = np.array([math.cos(angle / 2), 0.0, 0.0, math.sin(angle / 2)])
            return pos, quat

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
        """渲染一帧 RGB 图像。

        桩模式下返回带网格图案的测试图像。
        """
        if self._is_standalone:
            return self._stub_render(camera_name)

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
        elif self._is_standalone:
            # Stub mode always runs faster than real-time
            self.stats.real_time_factor = 10.0
        return self.stats

    # ── 内部方法：Isaac Sim 模式 ─────────────────────────

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

    # ── 内部方法：桩模式 ─────────────────────────────────

    def _init_stub_scene(self, scene: SimScene) -> None:
        """初始化桩模式场景状态。"""
        self._stub_time = 0.0
        self._stub_joints.clear()
        self._stub_sensors.clear()

        # 为每个机器人创建模拟关节
        for robot in scene.robots:
            # 默认关节：双臂 + 双腿 + 腰部 + 头部
            default_joints = {
                "left_shoulder_pitch": 0.0,
                "left_shoulder_roll": 0.0,
                "left_elbow": 0.0,
                "left_wrist_pitch": 0.0,
                "right_shoulder_pitch": 0.0,
                "right_shoulder_roll": 0.0,
                "right_elbow": 0.0,
                "right_wrist_pitch": 0.0,
                "left_hip_pitch": 0.0,
                "left_hip_roll": 0.0,
                "left_knee": 0.0,
                "left_ankle_pitch": 0.0,
                "right_hip_pitch": 0.0,
                "right_hip_roll": 0.0,
                "right_knee": 0.0,
                "right_ankle_pitch": 0.0,
                "waist_yaw": 0.0,
                "waist_pitch": 0.0,
                "neck_pitch": 0.0,
                "neck_yaw": 0.0,
            }
            # 使用机器人定义的执行器（如果有）
            if robot.actuators:
                default_joints = {name: 0.0 for name in robot.actuators}
            self._stub_joints[robot.name] = default_joints

        # 创建模拟传感器
        for robot in scene.robots:
            sensors = robot.sensors if robot.sensors else ["camera", "lidar", "imu"]
            for sensor_type in sensors:
                sensor_name = f"{robot.name}/{sensor_type}"
                self._stub_sensors[sensor_name] = self._create_stub_sensor(
                    sensor_name, sensor_type
                )

    def _stub_step(self) -> None:
        """桩模式单步推进。"""
        dt = self.config.time_step
        self._stub_time += dt

        # 更新模拟关节（简单的正弦运动）
        for robot_name, joints in self._stub_joints.items():
            for joint_name in joints:
                # 每个关节以不同频率做正弦运动
                freq = 0.5 + hash(f"{robot_name}/{joint_name}") % 100 * 0.01
                joints[joint_name] = 0.3 * math.sin(2 * math.pi * freq * self._stub_time)

        # 更新传感器时间戳
        for sensor in self._stub_sensors.values():
            sensor.timestamp = self._stub_time

    def _stub_apply_control(self, command: SimControlCommand) -> None:
        """桩模式控制指令处理。

        在桩模式下，控制指令直接写入模拟关节状态，
        用于测试控制回路逻辑。
        """
        joints = self._stub_joints.get(command.robot_name)
        if joints is None:
            logger.warning(f"[桩模式] 机器人不存在: {command.robot_name}")
            return

        if command.joint_names:
            for i, name in enumerate(command.joint_names):
                if i < len(command.targets) and name in joints:
                    joints[name] = float(command.targets[i])
        else:
            # 按顺序应用到关节
            joint_list = list(joints.keys())
            for i, target in enumerate(command.targets):
                if i < len(joint_list):
                    joints[joint_list[i]] = float(target)

        logger.debug(
            f"[桩模式] 控制: {command.robot_name} "
            f"{command.control_mode.value} "
            f"{len(command.targets)} targets"
        )

    def _get_stub_sensor_data(self, sensor_name: str) -> SimSensorData:
        """获取桩模式传感器数据。"""
        if sensor_name in self._stub_sensors:
            return self._stub_sensors[sensor_name]
        return self._create_stub_sensor(sensor_name, "joint_states")

    def _create_stub_sensor(self, name: str, sensor_type: str) -> SimSensorData:
        """创建模拟传感器数据。"""
        h, w = self.config.render_height, self.config.render_width

        if "camera" in sensor_type.lower() or "rgb" in sensor_type.lower():
            # 生成带网格的测试图像
            img = np.zeros((h, w, 3), dtype=np.uint8)
            grid_size = 64
            for i in range(0, h, grid_size):
                for j in range(0, w, grid_size):
                    if (i // grid_size + j // grid_size) % 2 == 0:
                        img[i:i + grid_size, j:j + grid_size] = [50, 50, 50]
                    else:
                        img[i:i + grid_size, j:j + grid_size] = [100, 100, 100]
            return SimSensorData(
                sensor_type=SensorType.RGB_CAMERA,
                timestamp=self._stub_time,
                data=img,
                frame_id=name,
                metadata={"stub": True, "width": w, "height": h},
            )
        elif "lidar" in sensor_type.lower():
            # 模拟环形 LiDAR 扫描
            angles = np.linspace(0, 2 * math.pi, 360)
            ranges = 2.0 + 0.5 * np.sin(angles * 3 + self._stub_time)
            return SimSensorData(
                sensor_type=SensorType.LIDAR,
                timestamp=self._stub_time,
                data={"angles": angles, "ranges": ranges},
                frame_id=name,
                metadata={"stub": True},
            )
        elif "imu" in sensor_type.lower():
            # 模拟 IMU 数据
            return SimSensorData(
                sensor_type=SensorType.IMU,
                timestamp=self._stub_time,
                data={
                    "ax": 0.1 * math.sin(self._stub_time),
                    "ay": 0.05 * math.cos(self._stub_time * 1.3),
                    "az": -9.81,
                    "gx": 0.01 * math.sin(self._stub_time * 0.7),
                    "gy": 0.01 * math.cos(self._stub_time * 0.5),
                    "gz": 0.005 * math.sin(self._stub_time * 0.3),
                },
                frame_id=name,
                metadata={"stub": True},
            )
        else:
            # 通用传感器数据
            return SimSensorData(
                sensor_type=SensorType.JOINT_STATES,
                timestamp=self._stub_time,
                data={"positions": {}, "velocities": {}},
                frame_id=name,
                metadata={"stub": True},
            )

    def _stub_render(self, camera_name: str = "") -> np.ndarray:
        """桩模式渲染：返回带网格图案的测试图像。"""
        h, w = self.config.render_height, self.config.render_width
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # 绘制网格背景
        grid_size = 32
        for i in range(0, h, grid_size):
            for j in range(0, w, grid_size):
                if (i // grid_size + j // grid_size) % 2 == 0:
                    img[i:i + grid_size, j:j + grid_size] = [40, 40, 40]
                else:
                    img[i:i + grid_size, j:j + grid_size] = [80, 80, 80]

        # 绘制十字准线
        cx, cy = w // 2, h // 2
        img[cy - 2:cy + 2, :] = [0, 255, 0]
        img[:, cx - 2:cx + 2] = [0, 255, 0]

        # 绘制时间戳
        ts_text = f"Stub Mode | t={self._stub_time:.1f}s"
        # Simple text rendering placeholder
        img[10:20, 10:10 + len(ts_text) * 6] = [255, 255, 255]

        return img
