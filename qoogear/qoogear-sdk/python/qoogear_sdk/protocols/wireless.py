"""无线通信库 — BLE / WiFi Direct"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class WirelessType(Enum):
    BLE = "ble"
    WIFI_DIRECT = "wifi_direct"
    UWB = "uwb"
    NFC = "nfc"


@dataclass
class WirelessDevice:
    """发现的无线设备"""
    name: str = ""
    address: str = ""
    device_type: WirelessType = WirelessType.BLE
    rssi: int = 0
    services: List[str] = field(default_factory=list)
    paired: bool = False
    connected: bool = False


class WirelessInterface:
    """无线通信接口。

    统一 BLE、WiFi Direct、UWB、NFC 的编程模型。
    支持设备发现、连接管理、GATT 服务操作。

    Usage:
        wifi = WirelessInterface(WirelessType.WIFI_DIRECT)
        devices = wifi.scan(timeout=5.0)
        wifi.connect(devices[0])
        wifi.send(b"hello")
    """

    def __init__(self, device_type: WirelessType = WirelessType.BLE):
        self._device_type = device_type
        self._connected = False
        self._connected_device: Optional[WirelessDevice] = None
        self._devices: List[WirelessDevice] = []
        self._lock = threading.RLock()
        self._callbacks: Dict[str, List[Callable]] = {
            "device_found": [],
            "connected": [],
            "disconnected": [],
            "data_received": [],
        }

    @property
    def device_type(self) -> WirelessType:
        return self._device_type

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def connected_device(self) -> Optional[WirelessDevice]:
        return self._connected_device

    # ---- 设备发现 ----

    def scan(self, timeout: float = 5.0) -> List[WirelessDevice]:
        """扫描附近的设备"""
        # 桩实现：返回模拟设备列表
        self._devices = [
            WirelessDevice(name="QooGrip-BLE", address="AA:BB:CC:DD:EE:01", device_type=WirelessType.BLE, rssi=-45),
            WirelessDevice(name="QooSense-WiFi", address="192.168.1.100", device_type=WirelessType.WIFI_DIRECT, rssi=-60),
        ]
        for dev in self._devices:
            self._fire_event("device_found", dev)
        return list(self._devices)

    # ---- 连接管理 ----

    def connect(self, device: WirelessDevice) -> bool:
        """连接设备"""
        with self._lock:
            self._connected = True
            self._connected_device = device
            self._fire_event("connected", device)
            return True

    def disconnect(self) -> None:
        """断开连接"""
        with self._lock:
            old = self._connected_device
            self._connected = False
            self._connected_device = None
            if old:
                self._fire_event("disconnected", old)

    # ---- 数据收发 ----

    def send(self, data: bytes) -> bool:
        """发送数据"""
        if not self._connected:
            return False
        return True

    def receive(self, timeout: float = 0.0) -> Optional[bytes]:
        """接收数据"""
        if not self._connected:
            return None
        return None

    # ---- BLE GATT 操作 ----

    def ble_read_characteristic(self, service_uuid: str, char_uuid: str) -> Optional[bytes]:
        """读取 BLE 特征值"""
        if self._device_type != WirelessType.BLE or not self._connected:
            return None
        return b""

    def ble_write_characteristic(self, service_uuid: str, char_uuid: str, data: bytes) -> bool:
        """写入 BLE 特征值"""
        if self._device_type != WirelessType.BLE or not self._connected:
            return False
        return True

    def ble_subscribe(self, service_uuid: str, char_uuid: str,
                      callback: Callable[[bytes], None]) -> bool:
        """订阅 BLE 通知"""
        if self._device_type != WirelessType.BLE or not self._connected:
            return False
        return True

    # ---- 事件 ----

    def on(self, event: str, callback: Callable) -> None:
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _fire_event(self, event: str, *args: Any) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args)
            except Exception:
                pass

    # ---- RSSI ----

    def get_rssi(self) -> int:
        """获取当前连接的信号强度"""
        if self._connected_device:
            return self._connected_device.rssi
        return -100
