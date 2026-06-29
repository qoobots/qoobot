# -*- coding: utf-8 -*-
"""PeopleService — 人物交互 Python 封装"""

import dataclasses
import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class FaceInfo:
    """人脸信息"""
    user_id: str = ""
    display_name: str = ""
    recognized: bool = False
    confidence: float = 0.0


@dataclasses.dataclass
class SearchResult:
    """人物搜索结果"""
    found: bool = False
    name: str = ""
    location: str = ""


class PeopleService:
    """
    人物交互服务 — 人脸识别、人物跟随、人物搜索、社交距离。
    """

    def __init__(self):
        self._initialized = False

    def initialize(self) -> bool:
        logger.info("PeopleService initializing...")
        self._initialized = True
        return True

    def on_face_detected(self, callback: Callable) -> None:
        """注册人脸检测回调"""
        logger.info("Face detection callback registered")

    def register_face(self, user_id: str, display_name: str,
                      image_path: str) -> bool:
        """注册人脸"""
        logger.info(f"Face registered: {display_name} ({user_id})")
        return True

    def unregister_face(self, user_id: str) -> bool:
        """删除人脸"""
        logger.info(f"Face unregistered: {user_id}")
        return True

    def follow_person(self, name: str, distance: float = 1.5) -> bool:
        """跟随指定人物"""
        logger.info(f"Following {name} at {distance}m")
        return True

    def stop_follow(self) -> bool:
        """停止跟随"""
        logger.info("Follow stopped")
        return True

    async def search_person(self, name: str, timeout_sec: float = 120) -> SearchResult:
        """搜索指定人物"""
        logger.info(f"Searching for {name} (timeout={timeout_sec}s)...")
        return SearchResult(found=False, name=name, location="")

    def set_social_distance(self, enable: bool, radius_m: float = 1.0) -> None:
        """设置社交距离"""
        logger.info(f"Social distance {'enabled' if enable else 'disabled'} (radius={radius_m}m)")

    def shutdown(self) -> None:
        logger.info("PeopleService shutting down")
        self._initialized = False
