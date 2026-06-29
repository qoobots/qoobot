"""配件模拟器"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..peripheral.base import AccessoryInfo, AccessoryState, AccessoryType, Capability


@dataclass
class SimulatorConfig:
    """模拟器配置"""
    accessory_type: AccessoryType = AccessoryType.END_EFFECTOR
    update_rate_hz: float = 50.0
    noise_enabled: bool = True
    noise_level: float = 0.01
    latency_ms: float = 5.0
    fail_probability: float = 0.0


class AccessorySimulator:
    """配件模拟器。

    在无硬件环境下模拟配件行为，用于开发和测试。
    支持末端执行器、传感器、电源等配件的虚拟仿真。

    Usage:
        sim = AccessorySimulator(SimulatorConfig(accessory_type=AccessoryType.END_EFFECTOR))
        sim.start()
        sim.set_command("grip_force", 50.0)
        state = sim.get_state()
    """

    def __init__(self, config: Optional[SimulatorConfig] = None):
        self._config = config or SimulatorConfig()
        self._running = False
        self._state = AccessoryState.DISCONNECTED
        self._info = AccessoryInfo(accessory_type=self._config.accessory_type)
        self._capabilities: Dict[str, Capability] = {}
        self._metrics: Dict[str, float] = {}
        self._commands: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, List[Callable]] = {}
        self._step_count: int = 0
        self._start_time: float = 0.0

        self._setup_default_capabilities()

    # ---- 生命周期 ----

    def start(self) -> bool:
        """启动模拟器"""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._start_time = time.monotonic()
            self._state = AccessoryState.CONNECTED
            self._state = AccessoryState.READY
            self._state = AccessoryState.ACTIVE
            self._thread = threading.Thread(target=self._sim_loop, daemon=True)
            self._thread.start()
            return True

    def stop(self) -> None:
        """停止模拟器"""
        with self._lock:
            self._running = False
            self._state = AccessoryState.DISCONNECTED
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ---- 命令 ----

    def set_command(self, capability_id: str, value: float) -> bool:
        """设置控制指令"""
        cap = self._capabilities.get(capability_id)
        if cap is None:
            return False
        if cap.is_readonly:
            return False
        value = max(cap.min_value, min(cap.max_value, value))
        self._commands[capability_id] = value
        return True

    def get_metric(self, metric_id: str) -> float:
        """读取传感器值"""
        return self._metrics.get(metric_id, 0.0)

    # ---- 状态 ----

    def get_state(self) -> Dict[str, Any]:
        """获取完整状态"""
        with self._lock:
            return {
                "state": self._state.value,
                "step_count": self._step_count,
                "uptime_seconds": time.monotonic() - self._start_time if self._start_time else 0,
                "capabilities": {k: {"value": self._metrics.get(k, v.default_value),
                                     "min": v.min_value, "max": v.max_value,
                                     "unit": v.unit}
                                 for k, v in self._capabilities.items()},
                "commands": dict(self._commands),
                "metrics": dict(self._metrics),
            }

    def inject_fault(self, fault_type: str) -> None:
        """注入故障（用于测试）"""
        self._state = AccessoryState.ERROR
        self._fire_event("fault", fault_type)

    # ---- 事件 ----

    def on(self, event: str, callback: Callable) -> None:
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    # ---- 内部 ----

    def _sim_loop(self) -> None:
        """模拟主循环"""
        period = 1.0 / max(self._config.update_rate_hz, 1.0)
        while self._running:
            loop_start = time.monotonic()
            self._step()
            elapsed = time.monotonic() - loop_start
            if elapsed < period:
                time.sleep(period - elapsed)

    def _step(self) -> None:
        """单步仿真"""
        with self._lock:
            self._step_count += 1

            # 模拟命令执行效果：命令值逐渐趋近传感器值
            for cap_id, cmd_value in self._commands.items():
                cap = self._capabilities.get(cap_id)
                if cap and not cap.is_readonly:
                    current = self._metrics.get(cap_id, cap.default_value)
                    # 一阶低通滤波模拟
                    alpha = 0.3
                    new_value = current + alpha * (cmd_value - current)
                    # 添加噪声
                    if self._config.noise_enabled:
                        import random
                        new_value += random.gauss(0, self._config.noise_level * abs(cap.max_value - cap.min_value))
                    self._metrics[cap_id] = max(cap.min_value, min(cap.max_value, new_value))

            # 模拟传感器数据更新
            for cap_id, cap in self._capabilities.items():
                if cap.is_readonly and cap_id not in self._metrics:
                    self._metrics[cap_id] = cap.default_value

    def _setup_default_capabilities(self) -> None:
        """根据类型设置默认能力"""
        if self._config.accessory_type == AccessoryType.END_EFFECTOR:
            self._capabilities = {
                "grip_force": Capability("grip_force", "Grip Force", unit="N", max_value=200.0, default_value=0.0),
                "grip_position": Capability("grip_position", "Grip Position", unit="mm", max_value=100.0, default_value=0.0),
                "grip_speed": Capability("grip_speed", "Grip Speed", unit="mm/s", max_value=500.0, default_value=100.0),
                "temperature": Capability("temperature", "Temperature", unit="°C", max_value=150.0, default_value=25.0, is_readonly=True),
                "current": Capability("current", "Current", unit="A", max_value=10.0, default_value=0.0, is_readonly=True),
            }
        elif self._config.accessory_type == AccessoryType.SENSOR:
            self._capabilities = {
                "sample_rate": Capability("sample_rate", "Sample Rate", unit="Hz", max_value=1000.0, default_value=10.0),
                "data_rate": Capability("data_rate", "Data Rate", unit="Mbps", max_value=10000.0, default_value=0.0, is_readonly=True),
                "temperature": Capability("temperature", "Temperature", unit="°C", max_value=125.0, default_value=25.0, is_readonly=True),
            }
        elif self._config.accessory_type == AccessoryType.POWER:
            self._capabilities = {
                "state_of_charge": Capability("state_of_charge", "SoC", unit="%", max_value=100.0, default_value=100.0, is_readonly=True),
                "voltage": Capability("voltage", "Voltage", unit="V", max_value=60.0, default_value=48.0, is_readonly=True),
                "temperature": Capability("temperature", "Temperature", unit="°C", max_value=80.0, default_value=25.0, is_readonly=True),
            }

    def _fire_event(self, event: str, *args: Any) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args)
            except Exception:
                pass
