"""多机器人管理 — 机器人列表、切换、分组

对应功能 CON-04（多机器人管理）。
"""

from __future__ import annotations

from typing import Callable, Optional

from console.core.models.session import RobotInfo


class RobotRegistry:
    """机器人注册表 — 管理已知机器人列表

    负责维护机器人列表、状态更新、选择切换。
    """

    def __init__(self) -> None:
        self._robots: dict[str, RobotInfo] = {}
        self._selected_id: Optional[str] = None

        # 回调
        self.on_robot_added: Optional[Callable[[RobotInfo], None]] = None
        self.on_robot_removed: Optional[Callable[[str], None]] = None
        self.on_robot_updated: Optional[Callable[[RobotInfo], None]] = None
        self.on_selection_changed: Optional[Callable[[Optional[str], Optional[str]], None]] = None

    @property
    def robots(self) -> list[RobotInfo]:
        return list(self._robots.values())

    @property
    def online_robots(self) -> list[RobotInfo]:
        return [r for r in self._robots.values() if r.status == "online"]

    @property
    def selected_robot(self) -> Optional[RobotInfo]:
        if self._selected_id:
            return self._robots.get(self._selected_id)
        return None

    @property
    def selected_id(self) -> Optional[str]:
        return self._selected_id

    def add_robot(self, robot: RobotInfo) -> None:
        """添加或更新机器人"""
        is_new = robot.robot_id not in self._robots
        self._robots[robot.robot_id] = robot
        if is_new and self.on_robot_added:
            self.on_robot_added(robot)
        elif not is_new and self.on_robot_updated:
            self.on_robot_updated(robot)

    def remove_robot(self, robot_id: str) -> None:
        """移除机器人"""
        if robot_id in self._robots:
            del self._robots[robot_id]
            if self._selected_id == robot_id:
                old = self._selected_id
                self._selected_id = None
                if self.on_selection_changed:
                    self.on_selection_changed(old, None)
            if self.on_robot_removed:
                self.on_robot_removed(robot_id)

    def select(self, robot_id: str) -> bool:
        """选择机器人"""
        if robot_id in self._robots:
            old = self._selected_id
            self._selected_id = robot_id
            if old != robot_id and self.on_selection_changed:
                self.on_selection_changed(old, robot_id)
            return True
        return False

    def get(self, robot_id: str) -> Optional[RobotInfo]:
        return self._robots.get(robot_id)

    def update_status(self, robot_id: str, status: str) -> None:
        """更新机器人状态"""
        robot = self._robots.get(robot_id)
        if robot:
            robot.status = status
            if self.on_robot_updated:
                self.on_robot_updated(robot)

    def get_by_group(self, group: str) -> list[RobotInfo]:
        """按分组获取机器人"""
        # 分组功能扩展点
        return [r for r in self._robots.values() if r.model == group]

    def clear(self) -> None:
        self._robots.clear()
        self._selected_id = None
