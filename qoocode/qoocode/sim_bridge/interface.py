"""Sim Bridge 核心接口定义。

所有仿真后端必须实现 SimBackend 抽象基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

import numpy as np


# ── 枚举 ────────────────────────────────────────────────

class SimState(Enum):
    """仿真器生命周期状态。"""
    UNINITIALIZED = auto()   # 未初始化
    LOADING = auto()          # 加载场景中
    READY = auto()            # 就绪，等待启动
    RUNNING = auto()          # 仿真运行中
    PAUSED = auto()           # 已暂停
    STOPPED = auto()          # 已停止
    ERROR = auto()            # 错误状态


class SensorType(Enum):
    """传感器类型枚举。"""
    RGB_CAMERA = "rgb_camera"
    DEPTH_CAMERA = "depth_camera"
    RGBD_CAMERA = "rgbd_camera"
    LIDAR = "lidar"
    IMU = "imu"
    JOINT_STATES = "joint_states"
    FORCE_TORQUE = "force_torque"
    CONTACT = "contact"
    GPS = "gps"
    ODOMETRY = "odometry"


class ControlMode(Enum):
    """机器人控制模式。"""
    POSITION = "position"          # 位置控制
    VELOCITY = "velocity"          # 速度控制
    TORQUE = "torque"              # 力矩控制
    END_EFFECTOR = "end_effector"  # 末端执行器位姿控制


# ── 数据类 ──────────────────────────────────────────────

@dataclass
class SimConfig:
    """仿真配置参数。"""
    backend: str = "mujoco"           # 后端名称: mujoco / isaac_sim / gazebo
    headless: bool = False            # 无头模式（无渲染）
    real_time: bool = True            # 实时模式 vs 最快速度
    time_step: float = 0.001          # 仿真时间步长 (秒)
    gravity: tuple[float, float, float] = (0.0, 0.0, -9.81)
    solver_iterations: int = 100      # 物理求解迭代次数
    integrator: str = "euler"         # 积分器: euler / rk4
    render_width: int = 1280
    render_height: int = 720
    enable_profiling: bool = False    # 启用性能剖析
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimScene:
    """仿真场景描述。"""
    name: str
    description: str = ""
    scene_path: Optional[str] = None         # 场景文件路径 (USD/MJCF/SDF)
    robots: list["SimRobot"] = field(default_factory=list)
    objects: list[dict[str, Any]] = field(default_factory=list)
    lights: list[dict[str, Any]] = field(default_factory=list)
    cameras: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimRobot:
    """仿真机器人描述。"""
    name: str
    model_path: str                         # 机器人模型路径
    base_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    base_orientation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    control_mode: ControlMode = ControlMode.POSITION
    fixed_base: bool = False
    actuators: dict[str, Any] = field(default_factory=dict)
    sensors: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimSensorData:
    """统一传感器数据容器。"""
    sensor_type: SensorType
    timestamp: float
    data: Any                                  # numpy array / dict
    frame_id: str = ""                         # 坐标系 ID
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimControlCommand:
    """统一控制指令。"""
    robot_name: str
    control_mode: ControlMode
    targets: np.ndarray                        # 目标值 (位置/速度/力矩)
    joint_names: list[str] = field(default_factory=list)
    timestamp: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimStats:
    """仿真性能统计。"""
    real_time_factor: float = 1.0              # 实时因子 (>1 快于实时)
    step_time_ms: float = 0.0                  # 每步耗时 (ms)
    physics_time_ms: float = 0.0               # 物理计算耗时 (ms)
    render_time_ms: float = 0.0                # 渲染耗时 (ms)
    sensor_time_ms: float = 0.0                # 传感器更新耗时 (ms)
    total_steps: int = 0
    total_time: float = 0.0


# ── 抽象基类 ────────────────────────────────────────────

class SimBackend(ABC):
    """仿真后端抽象基类。

    所有仿真引擎 (MuJoCo, Isaac Sim, Gazebo) 必须实现此接口。
    """

    def __init__(self, config: SimConfig):
        self.config = config
        self.state = SimState.UNINITIALIZED
        self.scene: Optional[SimScene] = None
        self.stats = SimStats()

    # ── 生命周期 ──────────────────────────────────────

    @abstractmethod
    def initialize(self) -> None:
        """初始化仿真引擎。"""
        ...

    @abstractmethod
    def load_scene(self, scene: SimScene) -> None:
        """加载场景。"""
        ...

    @abstractmethod
    def step(self) -> None:
        """推进一个仿真步长。"""
        ...

    @abstractmethod
    def reset(self) -> None:
        """重置仿真到初始状态。"""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """关闭仿真引擎，释放资源。"""
        ...

    # ── 状态控制 ──────────────────────────────────────

    @abstractmethod
    def pause(self) -> None:
        """暂停仿真。"""
        ...

    @abstractmethod
    def resume(self) -> None:
        """恢复仿真。"""
        ...

    # ── 传感器 ────────────────────────────────────────

    @abstractmethod
    def get_sensor_data(self, sensor_name: str) -> SimSensorData:
        """获取指定传感器的最新数据。"""
        ...

    @abstractmethod
    def get_all_sensor_data(self) -> list[SimSensorData]:
        """获取所有传感器的最新数据。"""
        ...

    # ── 控制 ──────────────────────────────────────────

    @abstractmethod
    def apply_control(self, command: SimControlCommand) -> None:
        """向指定机器人发送控制指令。"""
        ...

    @abstractmethod
    def get_joint_states(self, robot_name: str) -> dict[str, Any]:
        """获取机器人关节状态。"""
        ...

    # ── 场景查询 ──────────────────────────────────────

    @abstractmethod
    def get_robot_pose(self, robot_name: str) -> tuple[np.ndarray, np.ndarray]:
        """获取机器人位姿 (position, quaternion)。"""
        ...

    @abstractmethod
    def get_object_pose(self, object_name: str) -> tuple[np.ndarray, np.ndarray]:
        """获取物体位姿。"""
        ...

    # ── 渲染 ──────────────────────────────────────────

    @abstractmethod
    def render(self, camera_name: str = "") -> np.ndarray:
        """渲染一帧图像。

        Returns:
            RGB 图像 (H, W, 3) uint8 numpy array
        """
        ...

    # ── 工具 ──────────────────────────────────────────

    @abstractmethod
    def get_stats(self) -> SimStats:
        """获取性能统计。"""
        ...

    @property
    def is_running(self) -> bool:
        return self.state == SimState.RUNNING

    @property
    def is_ready(self) -> bool:
        return self.state in (SimState.READY, SimState.RUNNING, SimState.PAUSED)
