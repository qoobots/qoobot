"""末端执行器模板 — 夹具/吸盘/焊枪等"""

from __future__ import annotations

from .base import AccessoryBase, AccessoryInfo, AccessoryType, Capability


class GripperAccessory(AccessoryBase):
    """末端执行器配件基类。

    提供夹具、吸盘、焊枪等末端执行器的标准能力接口。
    子类只需实现 _initialize / _shutdown / _read_capability / _write_capability。
    """

    def __init__(self, info: AccessoryInfo | None = None):
        if info is None:
            info = AccessoryInfo(accessory_type=AccessoryType.END_EFFECTOR)
        super().__init__(info)

        # 注册标准末端执行器能力
        self.register_capability(Capability("grip_force", "Grip Force", "抓取力", "N", 0.0, 200.0, 50.0))
        self.register_capability(Capability("grip_position", "Grip Position", "夹爪位置", "mm", 0.0, 100.0, 0.0))
        self.register_capability(Capability("grip_speed", "Grip Speed", "抓取速度", "mm/s", 1.0, 500.0, 100.0))
        self.register_capability(Capability("temperature", "Temperature", "电机温度", "°C", 0.0, 150.0, 0.0, is_readonly=True))
        self.register_capability(Capability("current", "Current", "电机电流", "A", 0.0, 10.0, 0.0, is_readonly=True))

    # ---- 高级操作 ----

    def grasp(self, force_n: float = 50.0, speed_percent: float = 50.0, position_mm: float = 0.0) -> bool:
        """执行抓取操作"""
        if not self.is_active:
            return False
        self.set_capability_value("grip_speed", speed_percent * 5.0)  # percent to mm/s
        if position_mm > 0:
            self.set_capability_value("grip_position", position_mm)
        return self.set_capability_value("grip_force", force_n)

    def release(self, speed_percent: float = 50.0, open_position_mm: float = 100.0) -> bool:
        """释放抓取"""
        if not self.is_active:
            return False
        self.set_capability_value("grip_force", 0.0)
        self.set_capability_value("grip_speed", speed_percent * 5.0)
        return self.set_capability_value("grip_position", open_position_mm)

    def move_to(self, position_mm: float, speed_percent: float = 50.0) -> bool:
        """移动到指定位置"""
        if not self.is_active:
            return False
        self.set_capability_value("grip_speed", speed_percent * 5.0)
        return self.set_capability_value("grip_position", position_mm)

    def stop(self, emergency: bool = False) -> bool:
        """停止"""
        if emergency:
            return self.emergency_stop()
        self.set_capability_value("grip_speed", 0.0)
        return True

    @property
    def grip_force(self) -> float:
        return self.get_capability_value("grip_force") or 0.0

    @property
    def grip_position(self) -> float:
        return self.get_capability_value("grip_position") or 0.0

    @property
    def temperature(self) -> float:
        return self.get_capability_value("temperature") or 0.0

    @property
    def current(self) -> float:
        return self.get_capability_value("current") or 0.0

    # ---- 抽象方法默认桩实现 ----

    def _initialize(self) -> None:
        self._update_metric("grip_force", 0.0)
        self._update_metric("grip_position", 0.0)

    def _shutdown(self) -> None:
        pass

    def _read_capability(self, cap_id: str) -> float:
        return self._metrics.get(cap_id, 0.0)

    def _write_capability(self, cap_id: str, value: float) -> bool:
        self._update_metric(cap_id, value)
        return True
