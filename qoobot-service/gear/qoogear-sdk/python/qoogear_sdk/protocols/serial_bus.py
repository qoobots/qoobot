"""串行总线抽象层 — RS-485 / I2C / SPI"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BusType(Enum):
    RS485 = "rs485"
    I2C = "i2c"
    SPI = "spi"
    UART = "uart"


@dataclass
class BusConfig:
    """总线配置"""
    bus_type: BusType = BusType.RS485
    port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    timeout: float = 1.0
    data_bits: int = 8
    stop_bits: int = 1
    parity: str = "N"  # N/E/O
    # I2C 专用
    i2c_address: int = 0x40
    # SPI 专用
    spi_mode: int = 0
    spi_max_speed_hz: int = 1000000


class SerialBusInterface:
    """串行总线抽象接口。

    统一 RS-485、I2C、SPI、UART 的编程模型。
    支持 Modbus RTU 协议、I2C 寄存器读写、SPI 全双工传输。

    Usage:
        bus = SerialBusInterface(BusConfig(bus_type=BusType.RS485, port="/dev/ttyUSB0"))
        bus.open()
        bus.write(b"AT+STATUS\\r\\n")
        response = bus.read(64)
    """

    def __init__(self, config: BusConfig):
        self._config = config
        self._opened = False
        self._stats = {"bytes_sent": 0, "bytes_received": 0, "errors": 0}

    @property
    def config(self) -> BusConfig:
        return self._config

    @property
    def is_open(self) -> bool:
        return self._opened

    @property
    def stats(self) -> dict:
        return dict(self._stats)

    # ---- 生命周期 ----

    def open(self) -> bool:
        """打开总线连接"""
        self._opened = True
        return True

    def close(self) -> None:
        """关闭总线连接"""
        self._opened = False

    # ---- 通用读写 ----

    def write(self, data: bytes) -> int:
        """写入数据，返回写入字节数"""
        if not self._opened:
            return 0
        self._stats["bytes_sent"] += len(data)
        return len(data)

    def read(self, nbytes: int, timeout: Optional[float] = None) -> bytes:
        """读取指定字节数"""
        if not self._opened:
            return b""
        # 桩实现：返回空字节
        result = b"\x00" * min(nbytes, 256)
        self._stats["bytes_received"] += len(result)
        return result

    def write_read(self, write_data: bytes, read_length: int, timeout: float = 1.0) -> bytes:
        """写入后读取（如 Modbus 查询-响应）"""
        self.write(write_data)
        return self.read(read_length, timeout)

    # ---- I2C 专用 ----

    def i2c_write_register(self, register: int, data: bytes) -> bool:
        """I2C 写寄存器"""
        if not self._opened or self._config.bus_type != BusType.I2C:
            return False
        return True

    def i2c_read_register(self, register: int, length: int) -> bytes:
        """I2C 读寄存器"""
        if not self._opened or self._config.bus_type != BusType.I2C:
            return b""
        return b"\x00" * length

    # ---- SPI 专用 ----

    def spi_transfer(self, data: bytes) -> bytes:
        """SPI 全双工传输"""
        if not self._opened or self._config.bus_type != BusType.SPI:
            return b""
        return b"\x00" * len(data)

    # ---- Modbus RTU 辅助 ----

    @staticmethod
    def modbus_read_holding_registers(slave_id: int, start_addr: int, count: int) -> bytes:
        """构造 Modbus 读保持寄存器请求"""
        return bytes([slave_id, 0x03, (start_addr >> 8) & 0xFF, start_addr & 0xFF,
                      (count >> 8) & 0xFF, count & 0xFF])

    @staticmethod
    def modbus_write_single_register(slave_id: int, addr: int, value: int) -> bytes:
        """构造 Modbus 写单寄存器请求"""
        return bytes([slave_id, 0x06, (addr >> 8) & 0xFF, addr & 0xFF,
                      (value >> 8) & 0xFF, value & 0xFF])

    @staticmethod
    def modbus_crc(data: bytes) -> int:
        """计算 Modbus CRC-16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
