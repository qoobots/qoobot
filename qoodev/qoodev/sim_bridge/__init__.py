"""Sim Bridge — 统一仿真接口抽象层。

提供仿真引擎无关的接口抽象，使开发者技能代码可在
Isaac Sim / MuJoCo / Gazebo 等不同仿真器间无缝切换。
"""

from .interface import (
    SimBackend,
    SimState,
    SimConfig,
    SimSensorData,
    SimControlCommand,
    SimScene,
    SimRobot,
    SensorType,
    ControlMode,
)
from .manager import SimManager, register_backend, list_backends
from .scene_loader import SceneLoader, register_preset, list_presets
from .debugger import (
    LogStream,
    LogLevel,
    LogEntry,
    SensorVisualizer,
    SceneVisualizer,
    VariableMonitor,
    Profiler,
)

__all__ = [
    # 接口
    "SimBackend",
    "SimState",
    "SimConfig",
    "SimSensorData",
    "SimControlCommand",
    "SimScene",
    "SimRobot",
    "SensorType",
    "ControlMode",
    # 管理器
    "SimManager",
    "register_backend",
    "list_backends",
    "SceneLoader",
    "register_preset",
    "list_presets",
    # 调试与诊断
    "LogStream",
    "LogLevel",
    "LogEntry",
    "SensorVisualizer",
    "SceneVisualizer",
    "VariableMonitor",
    "Profiler",
]
