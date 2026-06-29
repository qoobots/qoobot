"""电源配件模板 — 电池/充电底座/无线充电"""

from __future__ import annotations

from .base import AccessoryBase, AccessoryInfo, AccessoryType, Capability, AccessoryState


class PowerAccessory(AccessoryBase):
    """电源配件基类。

    提供扩展电池、充电底座、无线充电等电源配件的标准接口。
    支持充放电管理、电源模式切换、电池健康监控。
    """

    def __init__(self, info: AccessoryInfo | None = None):
        if info is None:
            info = AccessoryInfo(accessory_type=AccessoryType.POWER)
        super().__init__(info)

        self._charging_enabled: bool = False
        self._power_mode: str = "normal"

        # 注册标准电源配件能力
        self.register_capability(Capability("state_of_charge", "State of Charge", "电池电量", "%", 0.0, 100.0, 100.0, is_readonly=True))
        self.register_capability(Capability("voltage", "Voltage", "电池电压", "V", 0.0, 60.0, 0.0, is_readonly=True))
        self.register_capability(Capability("current", "Current", "充放电电流", "A", -100.0, 100.0, 0.0, is_readonly=True))
        self.register_capability(Capability("temperature", "Temperature", "电池温度", "°C", -20.0, 80.0, 0.0, is_readonly=True))
        self.register_capability(Capability("cycle_count", "Cycle Count", "充放电循环次数", "cycles", 0.0, 10000.0, 0.0, is_readonly=True))
        self.register_capability(Capability("max_charge_current", "Max Charge Current", "最大充电电流", "A", 0.0, 50.0, 10.0))
        self.register_capability(Capability("target_soc", "Target SoC", "目标充电百分比", "%", 50.0, 100.0, 100.0))

    # ---- 电源操作 ----

    def enable_charging(self, max_current_a: float | None = None, target_soc_percent: float = 100.0) -> bool:
        """启用充电"""
        if not self.is_connected:
            return False
        if max_current_a is not None:
            self.set_capability_value("max_charge_current", max_current_a)
        self.set_capability_value("target_soc", target_soc_percent)
        self._charging_enabled = True
        return True

    def disable_charging(self) -> bool:
        """禁用充电"""
        self._charging_enabled = False
        return True

    def set_power_mode(self, mode: str) -> bool:
        """设置电源模式: normal / low_power / sleep / shutdown"""
        valid_modes = {"normal", "low_power", "sleep", "shutdown"}
        if mode not in valid_modes:
            self._add_error(f"Invalid power mode: {mode}. Must be one of {valid_modes}")
            return False
        self._power_mode = mode
        if mode == "shutdown":
            self.deactivate()
        return True

    def get_battery_health(self) -> dict:
        """获取电池健康报告"""
        return {
            "state_of_charge": self.get_capability_value("state_of_charge"),
            "voltage": self.get_capability_value("voltage"),
            "current": self.get_capability_value("current"),
            "temperature": self.get_capability_value("temperature"),
            "cycle_count": self.get_capability_value("cycle_count"),
            "charging": self._charging_enabled,
            "power_mode": self._power_mode,
            "is_healthy": self._state not in (AccessoryState.ERROR, AccessoryState.EMERGENCY_STOP),
        }

    # ---- 属性 ----

    @property
    def state_of_charge(self) -> float:
        return self.get_capability_value("state_of_charge") or 0.0

    @property
    def voltage(self) -> float:
        return self.get_capability_value("voltage") or 0.0

    @property
    def current(self) -> float:
        return self.get_capability_value("current") or 0.0

    @property
    def temperature(self) -> float:
        return self.get_capability_value("temperature") or 0.0

    @property
    def is_charging(self) -> bool:
        return self._charging_enabled

    @property
    def power_mode(self) -> str:
        return self._power_mode

    # ---- 抽象方法 ----

    def _initialize(self) -> None:
        self._update_metric("state_of_charge", 100.0)
        self._update_metric("voltage", 48.0)

    def _shutdown(self) -> None:
        self._charging_enabled = False

    def _read_capability(self, cap_id: str) -> float:
        return self._metrics.get(cap_id, 0.0)

    def _write_capability(self, cap_id: str, value: float) -> bool:
        self._update_metric(cap_id, value)
        return True

    def _on_emergency_stop(self) -> None:
        self._charging_enabled = False
        self._power_mode = "shutdown"
