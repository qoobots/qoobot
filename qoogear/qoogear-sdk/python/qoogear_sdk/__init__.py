"""
qoogear-sdk — QooBot 配件开发 SDK (Python)

Made for QooBot (MFQ) 认证体系的核心开发工具包。
提供配件基类、通信协议库、认证自检套件、配件模拟器等完整工具链。
"""

__version__ = "1.0.0"
__author__ = "QooBot Team"
__license__ = "Apache-2.0"

from .peripheral.base import AccessoryBase, AccessoryInfo, AccessoryState, AccessoryType, PhysicalInterface
from .peripheral.gripper import GripperAccessory
from .peripheral.sensor import SensorAccessory
from .peripheral.power import PowerAccessory
from .protocols.can import CANInterface
from .protocols.serial_bus import SerialBusInterface
from .protocols.wireless import WirelessInterface
from .testing import SelfCheckRunner
from .simulator import AccessorySimulator
from .utils.cert_verify import CertVerifier
from .utils.chip_auth import ChipAuthenticator

__all__ = [
    "__version__",
    "AccessoryBase",
    "AccessoryInfo",
    "AccessoryState",
    "AccessoryType",
    "PhysicalInterface",
    "GripperAccessory",
    "SensorAccessory",
    "PowerAccessory",
    "CANInterface",
    "SerialBusInterface",
    "WirelessInterface",
    "SelfCheckRunner",
    "AccessorySimulator",
    "CertVerifier",
    "ChipAuthenticator",
]
