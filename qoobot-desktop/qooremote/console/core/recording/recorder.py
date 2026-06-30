"""录制核心 — 多通道同步录制、精确回放、格式导出

对应功能 TCH-01/02/03（操作录制 + 回放 + 训练数据导出）。

录制文件格式：
- .qoorlog: 自定义二进制格式，包含同步的关节/传感器/视频/时间戳
- 支持导出为 .h5 (HDF5)、.jsonl、.csv 训练数据格式
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 录制模式
# ------------------------------------------------------------------

class RecordingMode(Enum):
    """录制模式"""
    FULL = "full"          # 全量录制（关节 + 传感器 + 视频 + 音频）（TCH-01）
    JOINTS_ONLY = "joints" # 仅关节
    SENSORS_ONLY = "sensors"
    VIDEO_ONLY = "video"


class RecordingState(Enum):
    """录制状态"""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


# ------------------------------------------------------------------
# 数据帧
# ------------------------------------------------------------------

@dataclass
class RecordingFrame:
    """单个录制帧 — 所有通道在同一时刻的快照"""
    timestamp: float              # Unix 时间戳（秒）
    frame_index: int              # 帧序号（从 0 开始）
    joint_angles: dict[str, float] = field(default_factory=dict)  # {joint_name: angle_rad}
    joint_velocities: dict[str, float] = field(default_factory=dict)
    joint_torques: dict[str, float] = field(default_factory=dict)
    end_effector_pose: Optional[list[float]] = None  # [x, y, z, qx, qy, qz, qw]
    imu: Optional[dict[str, float]] = None  # {accel_x/y/z, gyro_x/y/z}
    force_sensors: Optional[dict[str, float]] = None
    video_timestamp: Optional[float] = None  # 对应视频帧时间戳
    markers: list[str] = field(default_factory=list)  # 用户标记文本

    def to_dict(self) -> dict:
        return {
            "ts": self.timestamp,
            "idx": self.frame_index,
            "joints": self.joint_angles,
            "velocities": self.joint_velocities,
            "torques": self.joint_torques,
            "ee_pose": self.end_effector_pose,
            "imu": self.imu,
            "force": self.force_sensors,
            "video_ts": self.video_timestamp,
            "markers": self.markers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecordingFrame":
        return cls(
            timestamp=data.get("ts", 0),
            frame_index=data.get("idx", 0),
            joint_angles=data.get("joints", {}),
            joint_velocities=data.get("velocities", {}),
            joint_torques=data.get("torques", {}),
            end_effector_pose=data.get("ee_pose"),
            imu=data.get("imu"),
            force_sensors=data.get("force"),
            video_timestamp=data.get("video_ts"),
            markers=data.get("markers", []),
        )


# ------------------------------------------------------------------
# 录制会话元数据
# ------------------------------------------------------------------

@dataclass
class RecordingMetadata:
    """录制会话元信息"""
    session_id: str
    robot_id: str
    operator: str = "unknown"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    mode: RecordingMode = RecordingMode.FULL
    total_frames: int = 0
    total_duration_s: float = 0.0
    joint_names: list[str] = field(default_factory=list)
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "robot_id": self.robot_id,
            "operator": self.operator,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "mode": self.mode.value,
            "total_frames": self.total_frames,
            "total_duration_s": self.total_duration_s,
            "joint_names": self.joint_names,
            "notes": self.notes,
            "tags": self.tags,
        }


# ------------------------------------------------------------------
# 录制器
# ------------------------------------------------------------------

class Recorder:
    """多通道同步录制器

    采集关节角度、传感器读数、时间戳，并存入帧缓冲区。

    对应功能 TCH-01（操作录制）。
    """

    def __init__(self, max_buffer_frames: int = 100000) -> None:
        self._metadata: Optional[RecordingMetadata] = None
        self._state = RecordingState.IDLE
        self._frames: list[RecordingFrame] = []
        self._max_buffer = max_buffer_frames
        self._frame_idx = 0
        self._start_time = 0.0
        self._lock = Lock()
        self._marker_added = False

        # 回调
        self.on_state_change: Optional[Callable[[RecordingState], None]] = None
        self.on_frame_recorded: Optional[Callable[[int], None]] = None
        self.on_marker: Optional[Callable[[str, int], None]] = None

    # ---- 属性 ----

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def metadata(self) -> Optional[RecordingMetadata]:
        return self._metadata

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def elapsed(self) -> float:
        if self._state in (RecordingState.RECORDING, RecordingState.PAUSED):
            return time.time() - self._start_time
        return 0.0

    @property
    def is_recording(self) -> bool:
        return self._state == RecordingState.RECORDING

    # ---- 生命周期 ----

    def start(self, robot_id: str, operator: str = "unknown",
              mode: RecordingMode = RecordingMode.FULL,
              joint_names: Optional[list[str]] = None,
              notes: str = "") -> RecordingMetadata:
        """开始录制

        Args:
            robot_id: 机器人 ID
            operator: 操作员标识
            mode: 录制模式
            joint_names: 关节名称列表
            notes: 备注

        Returns:
            RecordingMetadata 录制元信息
        """
        with self._lock:
            self._frames.clear()
            self._frame_idx = 0
            self._start_time = time.time()
            self._metadata = RecordingMetadata(
                session_id=f"rec_{int(self._start_time * 1000)}",
                robot_id=robot_id,
                operator=operator,
                start_time=self._start_time,
                mode=mode,
                joint_names=joint_names or [],
                notes=notes,
            )
            self._transition_to(RecordingState.RECORDING)
            logger.info("Recording started: %s", self._metadata.session_id)
            return self._metadata

    def pause(self) -> None:
        """暂停录制"""
        if self._state == RecordingState.RECORDING:
            self._transition_to(RecordingState.PAUSED)
            logger.info("Recording paused at frame %d", self._frame_idx)

    def resume(self) -> None:
        """恢复录制"""
        if self._state == RecordingState.PAUSED:
            self._transition_to(RecordingState.RECORDING)
            logger.info("Recording resumed")

    def stop(self) -> RecordingMetadata:
        """停止录制

        Returns:
            RecordingMetadata 最终元信息
        """
        with self._lock:
            self._transition_to(RecordingState.STOPPED)
            if self._metadata:
                self._metadata.end_time = time.time()
                self._metadata.total_frames = len(self._frames)
                self._metadata.total_duration_s = self._metadata.end_time - self._metadata.start_time
            logger.info("Recording stopped: %d frames", len(self._frames))
            return self._metadata  # type: ignore[return-value]

    # ---- 数据采集 ----

    def record_frame(self, joint_angles: Optional[dict[str, float]] = None,
                     joint_velocities: Optional[dict[str, float]] = None,
                     joint_torques: Optional[dict[str, float]] = None,
                     end_effector_pose: Optional[list[float]] = None,
                     imu: Optional[dict[str, float]] = None,
                     force_sensors: Optional[dict[str, float]] = None,
                     video_ts: Optional[float] = None) -> Optional[RecordingFrame]:
        """记录一帧数据

        Args:
            joint_angles: 关节角度 {name: rad}
            joint_velocities: 关节速度 {name: rad/s}
            joint_torques: 关节力矩 {name: Nm}
            end_effector_pose: 末端位姿 [x,y,z,qx,qy,qz,qw]
            imu: IMU 数据
            force_sensors: 力传感器数据
            video_ts: 对应视频时间戳

        Returns:
            记录的数据帧，或 None（若未在录制）
        """
        if self._state != RecordingState.RECORDING:
            return None

        if len(self._frames) >= self._max_buffer:
            logger.warning("Recording buffer full (%d frames), dropping oldest", self._max_buffer)
            self._frames.pop(0)

        frame = RecordingFrame(
            timestamp=time.time(),
            frame_index=self._frame_idx,
            joint_angles=joint_angles or {},
            joint_velocities=joint_velocities or {},
            joint_torques=joint_torques or {},
            end_effector_pose=end_effector_pose,
            imu=imu,
            force_sensors=force_sensors,
            video_timestamp=video_ts,
        )

        with self._lock:
            self._frames.append(frame)
            self._frame_idx += 1

        if self.on_frame_recorded:
            self.on_frame_recorded(self._frame_idx)

        return frame

    def add_marker(self, text: str) -> None:
        """添加时间标记（用于动作标注 — TCH-04）"""
        if self._frames:
            self._frames[-1].markers.append(text)
            if self.on_marker:
                self.on_marker(text, self._frame_idx)

    # ---- 导出 ----

    def get_frames(self) -> list[RecordingFrame]:
        """获取所有录制帧"""
        with self._lock:
            return list(self._frames)

    def to_jsonl(self) -> str:
        """导出为 JSONL 格式"""
        return "\n".join(json.dumps(f.to_dict(), ensure_ascii=False) for f in self._frames)

    def to_hdf5(self) -> dict[str, np.ndarray]:
        """导出为 HDF5 兼容的字典格式（训练数据 — TCH-03）"""
        if not self._frames:
            return {}

        n = len(self._frames)
        joint_names = sorted(self._frames[0].joint_angles.keys()) if self._frames[0].joint_angles else []

        data: dict[str, np.ndarray] = {
            "timestamps": np.array([f.timestamp for f in self._frames], dtype=np.float64),
            "frame_indices": np.array([f.frame_index for f in self._frames], dtype=np.int32),
        }

        if joint_names:
            angles = np.zeros((n, len(joint_names)), dtype=np.float32)
            for i, f in enumerate(self._frames):
                for j, name in enumerate(joint_names):
                    angles[i, j] = f.joint_angles.get(name, 0.0)
            data["joint_angles"] = angles
            data["joint_names"] = np.array(joint_names, dtype="S")

        ee_poses = [f.end_effector_pose for f in self._frames if f.end_effector_pose]
        if ee_poses:
            data["end_effector_poses"] = np.array(ee_poses, dtype=np.float32)

        return data

    # ---- 内部 ----

    def _transition_to(self, state: RecordingState) -> None:
        old = self._state
        self._state = state
        if old != state and self.on_state_change:
            self.on_state_change(state)
