# -*- coding: utf-8 -*-
"""HMIService — 人机交互 Python 封装"""

import dataclasses
import enum
import logging
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ExpressionType(enum.Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    SURPRISED = "surprised"
    WORRIED = "worried"
    THINKING = "thinking"
    SLEEPING = "sleeping"


@dataclasses.dataclass
class Expression:
    """表情"""
    type: ExpressionType = ExpressionType.NEUTRAL
    intensity: float = 1.0  # 0.0 - 1.0


@dataclasses.dataclass
class LightState:
    """灯光状态"""
    pattern: str = "solid"  # solid/breathing/rotating/flashing/rainbow
    r: int = 255
    g: int = 255
    b: int = 255
    brightness: float = 1.0
    speed: float = 1.0


class HMIService:
    """
    人机交互服务 — 表情系统、灯光指示、触摸交互、手势识别、屏幕 UI。
    """

    def __init__(self):
        self._initialized = False

    def initialize(self) -> bool:
        logger.info("HMIService initializing...")
        self._initialized = True
        return True

    def set_expression(self, expr: Expression) -> bool:
        """设置表情"""
        logger.info(f"Expression set to {expr.type.value} (intensity={expr.intensity})")
        return True

    def play_expression_sequence(self, sequence: List[Expression],
                                  interval_ms: int = 500) -> bool:
        """播放表情序列"""
        logger.info(f"Playing expression sequence ({len(sequence)} frames)")
        return True

    def set_light(self, ring_id: str, state: LightState) -> bool:
        """设置指定灯环"""
        logger.info(f"Light '{ring_id}' set to {state.pattern} RGB({state.r},{state.g},{state.b})")
        return True

    def set_all_lights(self, state: LightState) -> bool:
        """设置所有灯环"""
        logger.info(f"All lights set to {state.pattern}")
        return True

    def on_touch(self, callback: Callable) -> None:
        """注册触摸事件回调"""
        logger.info("Touch callback registered")

    def on_gesture(self, callback: Callable) -> None:
        """注册手势识别回调"""
        logger.info("Gesture callback registered")

    def show_screen(self, screen_id: str) -> bool:
        """显示屏幕页面"""
        logger.info(f"Screen showing: {screen_id}")
        return True

    def update_screen_data(self, screen_id: str, data: dict) -> bool:
        """更新屏幕数据"""
        logger.info(f"Screen '{screen_id}' data updated")
        return True

    def hide_screen(self) -> bool:
        """隐藏屏幕"""
        logger.info("Screen hidden")
        return True

    def shutdown(self) -> None:
        logger.info("HMIService shutting down")
        self._initialized = False
