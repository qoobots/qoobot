"""遥控输入设备驱动

支持：
- 动作捕捉 (OptiTrack/XSens/Qualisys)
- VR 头显 (Meta Quest/SteamVR/OpenXR)
- 游戏手柄 (Xbox/DualSense/Switch Pro)
"""

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger("qoodev.teleop.drivers")


# ============================================================================
# 驱动数据帧
# ============================================================================

@dataclass
class MocapFrame:
    """动作捕捉数据帧"""
    timestamp_ns: int = 0
    bodies: List["MocapBody"] = field(default_factory=list)

    @dataclass
    class MocapBody:
        name: str = ""
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0)   # (x, y, z) in m
        orientation: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)  # (w, x, y, z)
        markers: List[Tuple[float, float, float]] = field(default_factory=list)


@dataclass
class VRFrame:
    """VR 头显数据帧"""
    timestamp_ns: int = 0
    headset_pose: Tuple[float, float, float, float, float, float, float] = (0, 0, 0, 1, 0, 0, 0)
    left_controller: Tuple[float, float, float, float, float, float, float] = (0, 0, 0, 1, 0, 0, 0)
    right_controller: Tuple[float, float, float, float, float, float, float] = (0, 0, 0, 1, 0, 0, 0)
    left_joystick: Tuple[float, float] = (0.0, 0.0)
    right_joystick: Tuple[float, float] = (0.0, 0.0)
    left_trigger: float = 0.0
    right_trigger: float = 0.0
    left_grip: float = 0.0
    right_grip: float = 0.0
    buttons: int = 0  # 按钮位掩码


@dataclass
class GamepadFrame:
    """游戏手柄数据帧"""
    timestamp_ns: int = 0
    left_stick: Tuple[float, float] = (0.0, 0.0)    # (-1, 1)
    right_stick: Tuple[float, float] = (0.0, 0.0)   # (-1, 1)
    left_trigger: float = 0.0                         # [0, 1]
    right_trigger: float = 0.0                        # [0, 1]
    dpad: Tuple[int, int] = (0, 0)                    # (-1, 0, 1)
    buttons: int = 0                                  # 按钮位掩码


# ============================================================================
# 驱动接口
# ============================================================================

class DriverInterface(ABC):
    """设备驱动抽象接口"""

    @abstractmethod
    def open(self) -> bool:
        """打开设备连接"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭设备连接"""
        pass

    @abstractmethod
    def poll(self) -> bool:
        """轮询设备状态，返回是否有新数据"""
        pass

    @abstractmethod
    def get_frame(self):
        """获取最新数据帧"""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """设备是否连接"""
        pass


# ============================================================================
# 动作捕捉驱动
# ============================================================================

class MotionCaptureDriver(DriverInterface):
    """动作捕捉设备驱动

    支持: OptiTrack (NatNet), XSens MVN, Qualisys QTM

    Usage:
        driver = MotionCaptureDriver(server="192.168.1.100", port=1510)
        driver.open()
        while True:
            if driver.poll():
                frame = driver.get_frame()
                # 映射到机器人运动...
    """

    # 动捕→机器人身体映射
    DEFAULT_BODY_MAP = {
        "Pelvis": "base",
        "Torso": "torso",
        "Head": "head",
        "LeftUpperArm": "arm_left_shoulder",
        "LeftForearm": "arm_left_elbow",
        "LeftHand": "arm_left_wrist",
        "RightUpperArm": "arm_right_shoulder",
        "RightForearm": "arm_right_elbow",
        "RightHand": "arm_right_wrist",
        "LeftUpperLeg": "leg_left_hip",
        "LeftLowerLeg": "leg_left_knee",
        "LeftFoot": "leg_left_ankle",
        "RightUpperLeg": "leg_right_hip",
        "RightLowerLeg": "leg_right_knee",
        "RightFoot": "leg_right_ankle",
    }

    def __init__(self, server: str = "localhost", port: int = 1510,
                 body_map: dict = None):
        self.server = server
        self.port = port
        self.body_map = body_map or self.DEFAULT_BODY_MAP
        self._connected = False
        self._latest_frame: Optional[MocapFrame] = None

    def open(self) -> bool:
        """连接到动捕服务器"""
        # 实际部署: 使用 NatNet SDK 或 XSens SDK
        logger.info(f"MotionCaptureDriver connecting to {self.server}:{self.port}")
        self._connected = True
        return True

    def close(self) -> None:
        """断开连接"""
        self._connected = False
        logger.info("MotionCaptureDriver disconnected")

    def poll(self) -> bool:
        """轮询新数据帧"""
        # 实际部署: 从 SDK 获取最新帧
        return False

    def get_frame(self) -> Optional[MocapFrame]:
        """获取最新动捕帧"""
        return self._latest_frame

    @property
    def is_connected(self) -> bool:
        return self._connected


# ============================================================================
# VR 头显驱动
# ============================================================================

class VRDriver(DriverInterface):
    """VR 头显驱动

    支持: Meta Quest (Oculus SDK), SteamVR (OpenVR), OpenXR

    Usage:
        driver = VRDriver()
        driver.open()
        while True:
            if driver.poll():
                frame = driver.get_frame()
                # 头部追踪 → 机器人头部
                # 手柄 → 末端执行器控制
    """

    def __init__(self):
        self._connected = False
        self._latest_frame: Optional[VRFrame] = None

    def open(self) -> bool:
        """初始化 VR 运行时"""
        logger.info("VRDriver initializing")
        self._connected = True
        return True

    def close(self) -> None:
        """释放 VR 资源"""
        self._connected = False

    def poll(self) -> bool:
        return False

    def get_frame(self) -> Optional[VRFrame]:
        return self._latest_frame

    @property
    def is_connected(self) -> bool:
        return self._connected


# ============================================================================
# 游戏手柄驱动
# ============================================================================

class GamepadDriver(DriverInterface):
    """游戏手柄驱动

    支持: Xbox Controller, DualSense (PS5), Switch Pro

    默认按键映射:
    - 左摇杆: 基座移动 (前进/后退/左右平移)
    - 右摇杆: 头部控制 (俯仰/偏航)
    - L1/R1: 末端执行器开/合
    - L2/R2: 手臂升降
    - A: 夹爪闭合, B: 夹爪张开
    - Start: 请求接管, Select: 交还自主
    - Y: 紧急停止

    Usage:
        driver = GamepadDriver()
        driver.open()
        while True:
            if driver.poll():
                frame = driver.get_frame()
                # 映射到 TeleopCommand...
    """

    # 按钮位掩码
    BUTTON_A = 1 << 0
    BUTTON_B = 1 << 1
    BUTTON_X = 1 << 2
    BUTTON_Y = 1 << 3
    BUTTON_LB = 1 << 4
    BUTTON_RB = 1 << 5
    BUTTON_START = 1 << 6
    BUTTON_SELECT = 1 << 7
    BUTTON_L3 = 1 << 8
    BUTTON_R3 = 1 << 9

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._connected = False
        self._latest_frame: Optional[GamepadFrame] = None

    def open(self) -> bool:
        """打开手柄设备"""
        # 实际部署: 使用 pygame.joystick 或 SDL2
        logger.info(f"GamepadDriver opening device {self.device_index}")
        self._connected = True
        return True

    def close(self) -> None:
        self._connected = False

    def poll(self) -> bool:
        return False

    def get_frame(self) -> Optional[GamepadFrame]:
        return self._latest_frame

    @property
    def is_connected(self) -> bool:
        return self._connected

    @staticmethod
    def apply_deadzone(value: float, deadzone: float = 0.1) -> float:
        """应用死区"""
        if abs(value) < deadzone:
            return 0.0
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - deadzone) / (1.0 - deadzone)

    @staticmethod
    def map_joystick_to_velocity(x: float, y: float,
                                  max_speed: float = 2.0) -> Tuple[float, float]:
        """将摇杆映射为基座速度指令"""
        x = GamepadDriver.apply_deadzone(x)
        y = GamepadDriver.apply_deadzone(y)
        magnitude = math.sqrt(x * x + y * y)
        if magnitude > 1.0:
            x /= magnitude
            y /= magnitude
        return x * max_speed, y * max_speed
