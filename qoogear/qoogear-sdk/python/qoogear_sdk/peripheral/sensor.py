"""传感器模组模板 — 视觉/力觉/触觉/环境传感器"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .base import AccessoryBase, AccessoryInfo, AccessoryType, Capability


class SensorAccessory(AccessoryBase):
    """传感器配件基类。

    提供视觉、深度、触觉、环境等传感器的标准接口。
    支持配置采样率、数据流控制和多通道读取。
    """

    def __init__(self, info: AccessoryInfo | None = None):
        if info is None:
            info = AccessoryInfo(accessory_type=AccessoryType.SENSOR)
        super().__init__(info)

        self._sample_rate_hz: float = 10.0
        self._streaming_enabled: bool = False
        self._active_channels: List[str] = []
        self._last_reading: Dict[str, Any] = {}
        self._reading_count: int = 0

        # 注册标准传感器能力
        self.register_capability(Capability("sample_rate", "Sample Rate", "采样率", "Hz", 0.1, 1000.0, 10.0))
        self.register_capability(Capability("data_rate", "Data Rate", "数据速率", "Mbps", 0.0, 10000.0, 0.0, is_readonly=True))
        self.register_capability(Capability("temperature", "Temperature", "传感器温度", "°C", -40.0, 125.0, 0.0, is_readonly=True))

    # ---- 传感器操作 ----

    def read(self) -> Dict[str, Any]:
        """读取传感器数据"""
        if not self.is_connected:
            return {}
        data = self._do_read()
        self._last_reading = data
        self._reading_count += 1
        self._update_metric("data_rate", len(str(data)) * self._sample_rate_hz / 1_000_000)
        return data

    def configure(self, sample_rate_hz: Optional[float] = None,
                  channels: Optional[List[str]] = None,
                  streaming: Optional[bool] = None,
                  config: Optional[Dict[str, str]] = None) -> bool:
        """配置传感器参数"""
        if sample_rate_hz is not None:
            self._sample_rate_hz = sample_rate_hz
            self._update_metric("sample_rate", sample_rate_hz)
        if channels is not None:
            self._active_channels = channels
        if streaming is not None:
            self._streaming_enabled = streaming
        if config is not None:
            self._do_configure(config)
        return True

    def enable_streaming(self) -> bool:
        """启用数据流"""
        self._streaming_enabled = True
        return True

    def disable_streaming(self) -> bool:
        """禁用数据流"""
        self._streaming_enabled = False
        return True

    def calibrate(self) -> bool:
        """执行传感器校准"""
        return self._do_calibrate()

    # ---- 属性 ----

    @property
    def sample_rate_hz(self) -> float:
        return self._sample_rate_hz

    @property
    def is_streaming(self) -> bool:
        return self._streaming_enabled

    @property
    def active_channels(self) -> List[str]:
        return list(self._active_channels)

    @property
    def last_reading(self) -> Dict[str, Any]:
        return dict(self._last_reading)

    @property
    def reading_count(self) -> int:
        return self._reading_count

    # ---- 抽象方法 (子类实现) ----

    def _do_read(self) -> Dict[str, Any]:
        """执行实际传感器读取 (子类实现)"""
        return {
            "timestamp": time.time(),
            "sample_rate": self._sample_rate_hz,
        }

    def _do_configure(self, config: Dict[str, str]) -> None:
        """执行传感器配置 (子类可选实现)"""
        pass

    def _do_calibrate(self) -> bool:
        """执行传感器校准 (子类可选实现)"""
        return True

    def _initialize(self) -> None:
        self._update_metric("sample_rate", self._sample_rate_hz)
        self._update_metric("data_rate", 0.0)

    def _shutdown(self) -> None:
        self._streaming_enabled = False

    def _read_capability(self, cap_id: str) -> float:
        return self._metrics.get(cap_id, 0.0)

    def _write_capability(self, cap_id: str, value: float) -> bool:
        if cap_id == "sample_rate":
            self._sample_rate_hz = value
        self._update_metric(cap_id, value)
        return True
