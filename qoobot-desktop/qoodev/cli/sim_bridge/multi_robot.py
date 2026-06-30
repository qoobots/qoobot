"""
多机器人仿真 — 同一场景多机器人协作仿真

提供多机器人场景管理、机器人间碰撞检测、任务分配接口。
支持 Isaac Sim 和 MuJoCo 后端。
"""

import logging
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RobotRole(Enum):
    LEADER = "leader"
    FOLLOWER = "follower"
    OBSERVER = "observer"
    WORKER = "worker"


@dataclass
class RobotInstance:
    name: str
    role: RobotRole = RobotRole.WORKER
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    orientation: List[float] = field(default_factory=lambda: [1.0, 0.0, 0.0, 0.0])
    active: bool = True
    collision_enabled: bool = True


@dataclass
class MultiRobotConfig:
    max_robots: int = 10
    collision_margin: float = 0.1  # 米
    enable_inter_robot_collision: bool = True
    enable_coordinated_tasks: bool = False
    sync_mode: str = "lockstep"  # lockstep | async
    physics_dt: float = 0.005


class MultiRobotSimulation:
    """多机器人仿真管理器"""

    def __init__(self, config: Optional[MultiRobotConfig] = None):
        self.config = config or MultiRobotConfig()
        self._robots: Dict[str, RobotInstance] = {}
        self._lock = threading.Lock()
        self._collision_callbacks: List[Callable] = []
        self._task_queue: List[Dict] = []

    def add_robot(self, name: str, role: RobotRole = RobotRole.WORKER,
                  position: Optional[List[float]] = None) -> RobotInstance:
        """添加机器人到仿真场景"""
        with self._lock:
            if len(self._robots) >= self.config.max_robots:
                raise RuntimeError(f"Maximum robot count ({self.config.max_robots}) exceeded")

            if name in self._robots:
                raise ValueError(f"Robot '{name}' already exists")

            robot = RobotInstance(
                name=name,
                role=role,
                position=position or [0.0, 0.0, 0.0],
            )
            self._robots[name] = robot
            logger.info(f"Added robot '{name}' (role={role.value}) to simulation")
            return robot

    def remove_robot(self, name: str) -> None:
        """移除机器人"""
        with self._lock:
            if name not in self._robots:
                raise ValueError(f"Robot '{name}' not found")
            del self._robots[name]
            logger.info(f"Removed robot '{name}' from simulation")

    def get_robot(self, name: str) -> Optional[RobotInstance]:
        """获取机器人实例"""
        return self._robots.get(name)

    def list_robots(self) -> List[str]:
        """列出所有机器人"""
        return list(self._robots.keys())

    def check_inter_robot_collision(self, robot_a: str, robot_b: str) -> bool:
        """检查两个机器人之间是否碰撞"""
        if not self.config.enable_inter_robot_collision:
            return False

        a = self._robots.get(robot_a)
        b = self._robots.get(robot_b)
        if not a or not b or not a.active or not b.active:
            return False

        # 简化：球体碰撞检测（基于包围球半径约 0.3m）
        dx = a.position[0] - b.position[0]
        dy = a.position[1] - b.position[1]
        dz = a.position[2] - b.position[2]
        dist = (dx * dx + dy * dy + dz * dz) ** 0.5
        min_dist = 0.6 + self.config.collision_margin  # 两个机器人的包围球半径和

        return dist < min_dist

    def get_nearby_robots(self, name: str, radius: float = 2.0) -> List[str]:
        """获取指定机器人附近的机器人列表"""
        target = self._robots.get(name)
        if not target:
            return []

        nearby = []
        for other_name, other in self._robots.items():
            if other_name == name or not other.active:
                continue
            dx = target.position[0] - other.position[0]
            dy = target.position[1] - other.position[1]
            dz = target.position[2] - other.position[2]
            if (dx * dx + dy * dy + dz * dz) ** 0.5 <= radius:
                nearby.append(other_name)

        return nearby

    def assign_task(self, task: Dict, robot_names: Optional[List[str]] = None) -> str:
        """分配任务给指定机器人（或自动分配）"""
        task_id = f"task_{len(self._task_queue):04d}"
        task["id"] = task_id
        task["assigned_robots"] = robot_names or []

        if self.config.enable_coordinated_tasks and not robot_names:
            # 自动分配：选择空闲机器人
            idle = [name for name, r in self._robots.items() if r.active and r.role != RobotRole.OBSERVER]
            task["assigned_robots"] = idle[:1]  # 默认分配一个

        self._task_queue.append(task)
        logger.info(f"Task '{task_id}' assigned to {task['assigned_robots']}")
        return task_id

    def on_collision(self, callback: Callable) -> None:
        """注册碰撞回调"""
        self._collision_callbacks.append(callback)

    def step(self) -> Dict:
        """执行一个仿真步进，返回碰撞和任务状态"""
        collisions = []

        # 检查机器人间碰撞
        robot_names = list(self._robots.keys())
        for i in range(len(robot_names)):
            for j in range(i + 1, len(robot_names)):
                if self.check_inter_robot_collision(robot_names[i], robot_names[j]):
                    collisions.append((robot_names[i], robot_names[j]))
                    for cb in self._collision_callbacks:
                        try:
                            cb(robot_names[i], robot_names[j])
                        except Exception as e:
                            logger.error(f"Collision callback error: {e}")

        return {
            "robot_count": len(self._robots),
            "active_robots": sum(1 for r in self._robots.values() if r.active),
            "collisions": collisions,
            "pending_tasks": len(self._task_queue),
        }

    def get_state(self) -> Dict:
        """获取所有机器人状态快照"""
        return {
            name: {
                "position": robot.position,
                "orientation": robot.orientation,
                "role": robot.role.value,
                "active": robot.active,
            }
            for name, robot in self._robots.items()
        }
