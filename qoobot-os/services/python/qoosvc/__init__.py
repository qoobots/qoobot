# -*- coding: utf-8 -*-
"""
qoosvc — QooBot 系统服务 Python SDK

提供机器人端系统服务的 Python API，包括：
  - 语音交互 (Voice)
  - 导航引擎 (Navigation)
  - 空间理解 (Spatial)
  - 自诊断 (Diagnostics)
  - 人机交互 (HMI)
  - 自主充电 (Charging)
  - 人物交互 (People)
  - 多机器人协同 (MultiRobot)
"""

__version__ = "0.3.0"
__author__ = "QooBot Team"

from qoosvc.voice import VoiceService
from qoosvc.navigation import NavigationService
from qoosvc.diagnostics import DiagnosticsService
from qoosvc.hmi import HMIService
from qoosvc.charging import ChargingService
from qoosvc.people import PeopleService
from qoosvc.multi_robot import MultiRobotService

__all__ = [
    "VoiceService",
    "NavigationService",
    "DiagnosticsService",
    "HMIService",
    "ChargingService",
    "PeopleService",
    "MultiRobotService",
]
