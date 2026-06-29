"""
硬件在环 (HIL) — 仿真环境连接真实硬件，虚实混合测试

支持部分传感器/执行器连接真实硬件，其余使用仿真。
用于验证感知/控制算法在实际硬件上的表现。
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HILMode(Enum):
    FULL_SIM = "full_simulation"
    FULL_HARDWARE = "full_hardware"
    MIXED = "mixed"


class DeviceType(Enum):
    CAMERA = "camera"
    LIDAR = "lidar"
    IMU = "imu"
    JOINT_MOTOR = "joint_motor"
    GRIPPER = "gripper"
    MICROPHONE = "microphone"
    SPEAKER = "speaker"


@dataclass
class HILDeviceConfig:
    device_type: DeviceType
    device_id: str
    use_hardware: bool = False
    hardware_uri: Optional[str] = None
    calibration_file: Optional[str] = None
    sync_enabled: bool = True


@dataclass
class HILConfig:
    mode: HILMode = HILMode.MIXED
    devices: List[HILDeviceConfig] = field(default_factory=list)
    sync_interval_ms: int = 10
    max_latency_tolerance_ms: int = 50
    enable_timestamp_sync: bool = True
    auto_fallback_to_sim: bool = True


@dataclass
class HILDataPacket:
    device_id: str
    device_type: DeviceType
    timestamp: float
    data: Any
    is_hardware: bool = False
    latency_ms: float = 0.0


class HardwareInterface:
    """真实硬件接口抽象"""

    def __init__(self, config: HILDeviceConfig):
        self.config = config
        self._connected = False
        self._last_data: Optional[HILDataPacket] = None

    def connect(self) -> bool:
        """连接硬件设备"""
        try:
            logger.info(f"Connecting to {self.config.device_type.value}:{self.config.device_id}")
            # 实际实现中会通过 SDK/驱动连接硬件
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.device_id}: {e}")
            return False

    def disconnect(self) -> None:
        """断开硬件连接"""
        self._connected = False

    def read(self) -> Optional[HILDataPacket]:
        """读取硬件数据"""
        if not self._connected:
            return None

        t0 = time.time()
        # 模拟从硬件读取数据
        data = {"status": "ok", "device": self.config.device_id}
        latency = (time.time() - t0) * 1000

        return HILDataPacket(
            device_id=self.config.device_id,
            device_type=self.config.device_type,
            timestamp=time.time(),
            data=data,
            is_hardware=True,
            latency_ms=latency,
        )

    def write(self, command: Dict) -> bool:
        """向硬件写入命令"""
        if not self._connected:
            return False
        logger.debug(f"Writing to {self.config.device_id}: {command}")
        return True

    @property
    def connected(self) -> bool:
        return self._connected


class HardwareInLoop:
    """硬件在环管理器"""

    def __init__(self, config: Optional[HILConfig] = None):
        self.config = config or HILConfig()
        self._devices: Dict[str, HardwareInterface] = {}
        self._sim_data: Dict[str, HILDataPacket] = {}
        self._callbacks: Dict[DeviceType, List[Callable]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def register_device(self, device_config: HILDeviceConfig) -> None:
        """注册设备配置"""
        key = f"{device_config.device_type.value}:{device_config.device_id}"
        if device_config.use_hardware:
            hw = HardwareInterface(device_config)
            hw.connect()
            self._devices[key] = hw
        logger.info(f"Registered device: {key} (hardware={device_config.use_hardware})")

    def feed_sim_data(self, device_id: str, device_type: DeviceType, data: Any) -> None:
        """从仿真环境输入数据"""
        key = f"{device_type.value}:{device_id}"
        self._sim_data[key] = HILDataPacket(
            device_id=device_id,
            device_type=device_type,
            timestamp=time.time(),
            data=data,
            is_hardware=False,
        )

    def get_data(self, device_id: str, device_type: DeviceType) -> Optional[HILDataPacket]:
        """获取设备数据（优先硬件，回退仿真）"""
        key = f"{device_type.value}:{device_id}"

        # 优先从硬件读取
        if key in self._devices:
            hw_data = self._devices[key].read()
            if hw_data:
                return hw_data

        # 回退到仿真数据
        return self._sim_data.get(key)

    def send_command(self, device_id: str, device_type: DeviceType, command: Dict) -> bool:
        """发送命令到设备"""
        key = f"{device_type.value}:{device_id}"
        if key in self._devices:
            return self._devices[key].write(command)
        logger.warning(f"Device {key} not found for command")
        return False

    def start(self) -> None:
        """启动 HIL 循环"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("HIL loop started")

    def stop(self) -> None:
        """停止 HIL 循环"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        for dev in self._devices.values():
            dev.disconnect()
        logger.info("HIL loop stopped")

    def on_data(self, device_type: DeviceType, callback: Callable) -> None:
        """注册数据回调"""
        if device_type not in self._callbacks:
            self._callbacks[device_type] = []
        self._callbacks[device_type].append(callback)

    def _run_loop(self) -> None:
        """HIL 主循环"""
        while self._running:
            with self._lock:
                for key, device in self._devices.items():
                    data = device.read()
                    if data:
                        device_type = data.device_type
                        for cb in self._callbacks.get(device_type, []):
                            try:
                                cb(data)
                            except Exception as e:
                                logger.error(f"HIL callback error: {e}")

            time.sleep(self.config.sync_interval_ms / 1000.0)

    def get_status(self) -> Dict:
        """获取 HIL 状态"""
        return {
            "mode": self.config.mode.value,
            "device_count": len(self._devices),
            "connected_devices": sum(1 for d in self._devices.values() if d.connected),
            "running": self._running,
        }
