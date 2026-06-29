"""遥控操作枚举类型定义"""

from enum import Enum, IntEnum


class RobotMode(str, Enum):
    """机器人运行模式"""
    AUTO = "AUTO"       # 完全自主
    HYBRID = "HYBRID"   # 混合模式
    TELEOP = "TELEOP"   # 完全遥控


class ControlMode(IntEnum):
    """控制模式"""
    POSITION = 0
    VELOCITY = 1
    TORQUE = 2
    IMPEDANCE = 3
    ADMITTANCE = 4


class SessionState(str, Enum):
    """遥控会话状态"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    TAKEOVER_PENDING = "TAKEOVER_PENDING"
    TELEOP_ACTIVE = "TELEOP_ACTIVE"
    HANDOVER_PENDING = "HANDOVER_PENDING"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class StopType(str, Enum):
    """紧急停止类型"""
    PROTECTIVE = "PROTECTIVE"   # 保护性停止
    EMERGENCY = "EMERGENCY"     # 紧急停止
    STO = "STO"                 # 安全转矩关断


class GripperType(IntEnum):
    """末端执行器类型"""
    PARALLEL = 0
    THREE_FINGER = 1
    SUCTION = 2
    DEXTEROUS = 3


class SafetyMode(str, Enum):
    """安全模式"""
    NORMAL = "NORMAL"
    REDUCED_SPEED = "REDUCED_SPEED"
    PROTECTIVE_STOP = "PROTECTIVE_STOP"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    STO = "STO"
    MAINTENANCE = "MAINTENANCE"


class VideoCodec(str, Enum):
    """视频编码器"""
    H264 = "H264"
    H265 = "H265"
    VP8 = "VP8"
    VP9 = "VP9"
    AV1 = "AV1"


class AudioCodec(str, Enum):
    """音频编码器"""
    OPUS = "OPUS"
    PCMU = "PCMU"
    PCMA = "PCMA"
