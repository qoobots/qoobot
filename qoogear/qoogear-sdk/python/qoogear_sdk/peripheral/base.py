"""配件基类 — MFQ 配件开发的抽象基类"""

from __future__ import annotations

import enum
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ============================================================================
# 枚举定义
# ============================================================================

class AccessoryType(enum.Enum):
    """配件类型 (对应 Protobuf AccessoryType)"""
    END_EFFECTOR = "end_effector"
    SENSOR = "sensor"
    WEARABLE = "wearable"
    POWER = "power"
    MOBILITY = "mobility"
    COMMUNICATION = "communication"
    TOOL = "tool"


class AccessoryState(enum.Enum):
    """配件状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    ACTIVE = "active"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    FIRMWARE_UPDATE = "firmware_update"


class PhysicalInterface(enum.Enum):
    """物理接口类型"""
    CAN_FD = "can_fd"
    RS485 = "rs485"
    ETHERNET = "ethernet"
    USB_3 = "usb3"
    I2C = "i2c"
    SPI = "spi"
    BLUETOOTH_LE = "ble"
    WIFI_DIRECT = "wifi_direct"
    MAGSAFE = "magsafe"


class MfqCertLevel(enum.Enum):
    """MFQ 认证等级"""
    BASIC = "basic"
    PREMIUM = "premium"
    PRO = "pro"


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class AccessoryInfo:
    """配件识别信息"""
    vendor_id: int = 0
    product_id: int = 0
    serial_number: int = 0
    hardware_version: int = 1
    name: str = ""
    vendor_name: str = ""
    model: str = ""
    firmware_version: str = "0.0.1"
    accessory_type: AccessoryType = AccessoryType.END_EFFECTOR
    phy_interface: PhysicalInterface = PhysicalInterface.CAN_FD
    mfq_cert_hash: str = ""
    mfq_level: MfqCertLevel = MfqCertLevel.BASIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "serial_number": self.serial_number,
            "hardware_version": self.hardware_version,
            "name": self.name,
            "vendor_name": self.vendor_name,
            "model": self.model,
            "firmware_version": self.firmware_version,
            "accessory_type": self.accessory_type.value,
            "phy_interface": self.phy_interface.value,
            "mfq_cert_hash": self.mfq_cert_hash,
            "mfq_level": self.mfq_level.value,
        }

    @property
    def accessory_id(self) -> str:
        """唯一配件标识符"""
        return f"{self.vendor_id:04X}:{self.product_id:04X}:{self.serial_number:08X}"


@dataclass
class Capability:
    """单项能力定义"""
    capability_id: str
    name: str
    description: str = ""
    unit: str = ""
    min_value: float = 0.0
    max_value: float = 100.0
    default_value: float = 0.0
    is_readonly: bool = False
    parameters: Dict[str, str] = field(default_factory=dict)


@dataclass
class AccessoryStatus:
    """配件状态快照"""
    state: AccessoryState = AccessoryState.DISCONNECTED
    uptime_seconds: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    active_errors: List[str] = field(default_factory=list)
    cpu_usage_percent: float = 0.0
    memory_usage_kb: float = 0.0


# ============================================================================
# 配件基类
# ============================================================================

class AccessoryBase(ABC):
    """MFQ 配件抽象基类。

    所有第三方配件驱动都应继承此类，实现相应抽象方法。
    提供完整的生命周期管理、事件回调、状态追踪和健康监控。

    Usage:
        class MyGripper(AccessoryBase):
            def _initialize(self):
                pass

            def _shutdown(self):
                pass

            def _read_capability(self, cap_id):
                return 0.0

            def _write_capability(self, cap_id, value):
                return True
    """

    def __init__(self, info: Optional[AccessoryInfo] = None):
        self._info = info or AccessoryInfo()
        self._state = AccessoryState.DISCONNECTED
        self._capabilities: Dict[str, Capability] = {}
        self._start_time: float = 0.0
        self._lock = threading.RLock()
        self._event_handlers: Dict[str, List[Callable]] = {
            "state_change": [],
            "error": [],
            "connected": [],
            "disconnected": [],
            "metric_alert": [],
        }
        self._metrics: Dict[str, float] = {}
        self._errors: List[str] = []
        self._initialized = False

    # ---- 属性 ----

    @property
    def info(self) -> AccessoryInfo:
        return self._info

    @property
    def state(self) -> AccessoryState:
        return self._state

    @property
    def capabilities(self) -> Dict[str, Capability]:
        return dict(self._capabilities)

    @property
    def is_connected(self) -> bool:
        return self._state in (AccessoryState.CONNECTED, AccessoryState.READY, AccessoryState.ACTIVE)

    @property
    def is_active(self) -> bool:
        return self._state == AccessoryState.ACTIVE

    @property
    def uptime_seconds(self) -> float:
        if self._start_time == 0:
            return 0.0
        return time.monotonic() - self._start_time

    # ---- 生命周期 (公共接口) ----

    def connect(self) -> bool:
        """连接到配件"""
        with self._lock:
            if self._state != AccessoryState.DISCONNECTED:
                return False
            self._set_state(AccessoryState.CONNECTING)
            try:
                self._initialize()
                self._initialized = True
                self._start_time = time.monotonic()
                self._set_state(AccessoryState.CONNECTED)
                self._set_state(AccessoryState.READY)
                self._fire_event("connected", self)
                return True
            except Exception as e:
                self._add_error(f"Connection failed: {e}")
                self._set_state(AccessoryState.ERROR)
                return False

    def activate(self) -> bool:
        """激活配件 (准备执行操作)"""
        with self._lock:
            if self._state != AccessoryState.READY:
                return False
            try:
                self._on_activate()
                self._set_state(AccessoryState.ACTIVE)
                return True
            except Exception as e:
                self._add_error(f"Activation failed: {e}")
                return False

    def deactivate(self) -> bool:
        """停用配件"""
        with self._lock:
            if self._state != AccessoryState.ACTIVE:
                return False
            try:
                self._on_deactivate()
                self._set_state(AccessoryState.READY)
                return True
            except Exception as e:
                self._add_error(f"Deactivation failed: {e}")
                return False

    def disconnect(self) -> bool:
        """断开连接"""
        with self._lock:
            try:
                if self._state == AccessoryState.ACTIVE:
                    self._on_deactivate()
                self._shutdown()
                self._initialized = False
                self._set_state(AccessoryState.DISCONNECTED)
                self._fire_event("disconnected", self)
                return True
            except Exception as e:
                self._add_error(f"Disconnection failed: {e}")
                return False

    def emergency_stop(self) -> bool:
        """紧急停止"""
        with self._lock:
            try:
                self._on_emergency_stop()
                self._set_state(AccessoryState.EMERGENCY_STOP)
                return True
            except Exception as e:
                self._add_error(f"Emergency stop failed: {e}")
                return False

    # ---- 能力管理 ----

    def register_capability(self, cap: Capability) -> None:
        """注册配件能力"""
        with self._lock:
            self._capabilities[cap.capability_id] = cap

    def get_capability(self, cap_id: str) -> Optional[Capability]:
        """获取指定能力"""
        return self._capabilities.get(cap_id)

    def get_capability_value(self, cap_id: str) -> Optional[float]:
        """读取能力值 (传感器类)"""
        cap = self._capabilities.get(cap_id)
        if cap is None:
            return None
        return self._read_capability(cap_id)

    def set_capability_value(self, cap_id: str, value: float) -> bool:
        """设置能力值 (执行器类)"""
        cap = self._capabilities.get(cap_id)
        if cap is None:
            self._add_error(f"Unknown capability: {cap_id}")
            return False
        if cap.is_readonly:
            self._add_error(f"Capability {cap_id} is read-only")
            return False
        if value < cap.min_value or value > cap.max_value:
            self._add_error(f"Value {value} out of range [{cap.min_value}, {cap.max_value}] for {cap_id}")
            return False
        return self._write_capability(cap_id, value)

    # ---- 状态与健康 ----

    def get_status(self) -> AccessoryStatus:
        """获取当前状态快照"""
        return AccessoryStatus(
            state=self._state,
            uptime_seconds=int(self.uptime_seconds),
            metrics=dict(self._metrics),
            active_errors=list(self._errors),
        )

    def get_health(self) -> Dict[str, Any]:
        """获取健康状态报告"""
        return {
            "accessory_id": self._info.accessory_id,
            "state": self._state.value,
            "is_healthy": self._state not in (AccessoryState.ERROR, AccessoryState.EMERGENCY_STOP),
            "uptime_s": int(self.uptime_seconds),
            "errors": list(self._errors),
            "metrics": dict(self._metrics),
            "capability_count": len(self._capabilities),
        }

    def clear_errors(self) -> None:
        """清除错误列表"""
        with self._lock:
            self._errors.clear()

    # ---- 事件系统 ----

    def on(self, event: str, handler: Callable) -> None:
        """注册事件处理器"""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """移除事件处理器"""
        if event in self._event_handlers:
            self._event_handlers[event] = [h for h in self._event_handlers[event] if h is not handler]

    # ---- 抽象方法 (子类实现) ----

    @abstractmethod
    def _initialize(self) -> None:
        """初始化硬件连接 (子类实现)"""
        ...

    @abstractmethod
    def _shutdown(self) -> None:
        """关闭硬件连接 (子类实现)"""
        ...

    @abstractmethod
    def _read_capability(self, cap_id: str) -> float:
        """读取能力值 (子类实现)"""
        ...

    @abstractmethod
    def _write_capability(self, cap_id: str, value: float) -> bool:
        """写入能力值 (子类实现)"""
        ...

    def _on_activate(self) -> None:
        """激活回调 (子类可选重写)"""
        pass

    def _on_deactivate(self) -> None:
        """停用回调 (子类可选重写)"""
        pass

    def _on_emergency_stop(self) -> None:
        """紧急停止回调 (子类可选重写)"""
        pass

    # ---- 内部方法 ----

    def _set_state(self, new_state: AccessoryState) -> None:
        old_state = self._state
        self._state = new_state
        if old_state != new_state:
            self._fire_event("state_change", old_state, new_state)

    def _add_error(self, message: str) -> None:
        self._errors.append(message)
        self._fire_event("error", message)

    def _update_metric(self, name: str, value: float) -> None:
        self._metrics[name] = value

    def _fire_event(self, event: str, *args: Any) -> None:
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(*args)
            except Exception:
                pass  # 事件处理器异常不应影响配件运行

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self._info.accessory_id}, state={self._state.value})>"
