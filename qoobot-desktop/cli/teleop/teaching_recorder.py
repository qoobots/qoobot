"""示教录制器

在遥控操作过程中同步采集多模态数据：
- 关节轨迹 (100Hz)
- 操作员指令
- 传感器快照 (视频/IMU/力觉)
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("qoodev.teleop.teaching")


@dataclass
class TeachingFrame:
    """示教数据帧"""
    timestamp_ns: int = 0
    frame_index: int = 0

    # 关节轨迹
    joint_positions: Dict[str, float] = field(default_factory=dict)
    joint_velocities: Dict[str, float] = field(default_factory=dict)
    joint_torques: Dict[str, float] = field(default_factory=dict)

    # 基座
    base_x: float = 0.0
    base_y: float = 0.0
    base_theta: float = 0.0

    # 末端执行器
    left_gripper_position: float = 0.0
    right_gripper_position: float = 0.0
    left_gripper_force: float = 0.0
    right_gripper_force: float = 0.0

    # 操作员指令 (用于行为克隆)
    operator_command: Optional[dict] = None

    # 传感器快照 (可选)
    sensor_data: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "timestamp_ns": self.timestamp_ns,
            "frame_index": self.frame_index,
            "joint_positions": self.joint_positions,
            "joint_velocities": self.joint_velocities,
            "joint_torques": self.joint_torques,
            "base": {"x": self.base_x, "y": self.base_y, "theta": self.base_theta},
            "left_gripper": {"position": self.left_gripper_position, "force": self.left_gripper_force},
            "right_gripper": {"position": self.right_gripper_position, "force": self.right_gripper_force},
            "operator_command": self.operator_command,
            "sensor_data": self.sensor_data
        }


class TeachingRecorder:
    """示教录制器

    在遥控操作时同步采集多模态示教数据。

    Usage:
        recorder = TeachingRecorder("output/teaching_record")
        recorder.start("pick_and_place", "Pick and place task", tags=["grasping"])
        # ... 遥控操作中 ...
        recorder.record_frame(frame)
        recorder.stop()
    """

    def __init__(self, output_dir: str = "teaching_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._recording = False
        self._start_time = 0.0
        self._frame_count = 0
        self._metadata: Dict[str, Any] = {}
        self._frames: List[TeachingFrame] = []
        self._tags: List[str] = []

    def start(self, name: str, description: str = "",
              tags: List[str] = None,
              operator: str = "", robot_id: str = "") -> None:
        """开始录制"""
        if self._recording:
            logger.warning("Already recording")
            return

        self._recording = True
        self._start_time = time.time()
        self._frame_count = 0
        self._frames = []
        self._tags = tags or []

        self._metadata = {
            "name": name,
            "description": description,
            "tags": self._tags,
            "operator": operator,
            "robot_id": robot_id,
            "start_time": datetime.now().isoformat(),
            "data_format": "qoodev.teaching.v1"
        }

        logger.info(f"Teaching recording started: {name}")

    def record_frame(self, frame: TeachingFrame) -> None:
        """记录一帧示教数据"""
        if not self._recording:
            return

        frame.frame_index = self._frame_count
        self._frames.append(frame)
        self._frame_count += 1

    def stop(self) -> Optional[str]:
        """停止录制并保存到磁盘"""
        if not self._recording:
            return None

        self._recording = False
        duration = time.time() - self._start_time

        self._metadata["end_time"] = datetime.now().isoformat()
        self._metadata["duration_s"] = duration
        self._metadata["frame_count"] = self._frame_count
        self._metadata["avg_frame_rate"] = self._frame_count / max(duration, 0.001)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_slug = self._metadata["name"].replace(" ", "_").lower()
        filename = f"{timestamp}_{name_slug}.json"
        filepath = self.output_dir / filename

        # 保存
        data = {
            "metadata": self._metadata,
            "frames": [f.to_dict() for f in self._frames]
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        file_size = filepath.stat().st_size
        logger.info(f"Teaching recording saved: {filepath} "
                     f"({self._frame_count} frames, {duration:.1f}s, {file_size / 1024:.1f} KB)")

        return str(filepath)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def duration(self) -> float:
        if not self._recording:
            return 0.0
        return time.time() - self._start_time

    @staticmethod
    def load(filepath: str) -> dict:
        """加载示教记录"""
        with open(filepath, "r") as f:
            return json.load(f)
