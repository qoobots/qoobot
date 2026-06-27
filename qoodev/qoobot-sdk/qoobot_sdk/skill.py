"""
QooSkill - Base class for all QooBot skills.

A skill is the fundamental unit of QooBot application development.
It encapsulates a specific capability that runs on the Brain OS platform.

Lifecycle:
    init -> on_start -> [on_tick loop] -> on_pause -> on_resume -> on_stop

Example:
    from qoobot_sdk import QooSkill, SkillContext

    class MySkill(QooSkill):
        async def on_start(self, ctx):
            ctx.logger.info("Skill started")

        async def on_tick(self, ctx):
            # Main logic per control cycle
            pass
"""

from __future__ import annotations

import asyncio
import logging
import signal
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, Awaitable


class SkillState(Enum):
    """Skill lifecycle states."""
    CREATED = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


@dataclass
class SkillContext:
    """Context passed to skill lifecycle methods.

    Provides access to runtime services and sensor data.
    """
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("qoobot.skill"))
    state: SkillState = SkillState.CREATED
    tick_count: int = 0
    config: dict = field(default_factory=dict)

    # Sensor data (populated at runtime)
    camera_rgb: Optional["Image"] = None       # type: ignore
    camera_depth: Optional["DepthMap"] = None  # type: ignore
    lidar_points: Optional["PointCloud"] = None  # type: ignore
    imu_data: Optional["IMUData"] = None       # type: ignore
    joint_states: Optional["JointStates"] = None  # type: ignore


class QooSkill(ABC):
    """Base class for QooBot skills.

    Subclass this to create a QooBot skill. Override lifecycle methods
    to implement your skill's behavior.

    Attributes:
        name: Skill display name
        version: Semantic version string
        state: Current lifecycle state
    """

    def __init__(self, name: str = "unnamed", version: str = "0.1.0"):
        self.name = name
        self.version = version
        self.state = SkillState.CREATED
        self._ctx = SkillContext()
        self._stop_event = asyncio.Event()

    async def run(self, config: Optional[dict] = None) -> None:
        """Run the skill through its full lifecycle.

        This is the main entry point. It handles state transitions
        and the main control loop.

        Args:
            config: Optional configuration dictionary
        """
        if config:
            self._ctx.config = config

        self._ctx.logger = logging.getLogger(f"qoobot.skill.{self.name}")

        try:
            self.state = SkillState.STARTING
            await self.on_start(self._ctx)

            self.state = SkillState.RUNNING
            await self._main_loop()

        except asyncio.CancelledError:
            self._ctx.logger.info("Skill cancelled")
        except Exception as e:
            self._ctx.logger.error(f"Skill error: {e}", exc_info=True)
            self.state = SkillState.ERROR
        finally:
            self.state = SkillState.STOPPING
            await self.on_stop(self._ctx)
            self.state = SkillState.STOPPED

    async def _main_loop(self) -> None:
        """Main control loop - calls on_tick each cycle."""
        while not self._stop_event.is_set():
            try:
                await self.on_tick(self._ctx)
                self._ctx.tick_count += 1
                await asyncio.sleep(0.01)  # ~100Hz default
            except Exception as e:
                self._ctx.logger.error(f"Tick error: {e}")

    def stop(self) -> None:
        """Request graceful stop of the skill."""
        self._stop_event.set()

    def pause(self) -> None:
        """Request pause of the skill."""
        self.state = SkillState.PAUSED

    def resume(self) -> None:
        """Resume a paused skill."""
        self.state = SkillState.RUNNING

    # --- Lifecycle hooks (override in subclasses) ---

    async def on_start(self, ctx: SkillContext) -> None:
        """Called when the skill starts. Override for initialization."""
        ctx.logger.info(f"Skill {self.name} v{self.version} started")

    async def on_stop(self, ctx: SkillContext) -> None:
        """Called when the skill stops. Override for cleanup."""
        ctx.logger.info(f"Skill {self.name} stopped")

    async def on_tick(self, ctx: SkillContext) -> None:
        """Called each control cycle. Override with main logic."""
        pass

    async def on_pause(self, ctx: SkillContext) -> None:
        """Called when the skill is paused."""
        pass

    async def on_resume(self, ctx: SkillContext) -> None:
        """Called when the skill resumes from pause."""
        pass

    async def on_error(self, ctx: SkillContext, error: Exception) -> None:
        """Called when an unhandled error occurs."""
        ctx.logger.error(f"Unhandled error: {error}")
