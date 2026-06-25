"""brain_os SDK — 统一客户端入口"""

from __future__ import annotations

from .config import BrainOSConfig
from .connection import GrpcConnection, AsyncGrpcConnection
from .cognition.intent_api import IntentAPI
from .cognition.task_api import TaskAPI
from .decision.plan_api import PlanAPI
from .decision.trajectory_api import TrajectoryAPI
from .perception.scene_api import SceneAPI
from .perception.object_api import ObjectAPI
from .control.motion_api import MotionAPI
from .control.gripper_api import GripperAPI
from .control.direct_control import DirectController
from .safety.safety_api import SafetyAPI
from .safety.emergency_api import EmergencyAPI
from .knowledge.search_api import KnowledgeSearchAPI
from .knowledge.episode_api import EpisodeAPI
from .speech.speech_api import SpeechAPI


class BrainOSClient:
    """
    Brain OS Python SDK 统一客户端。

    使用示例::

        client = BrainOSClient()
        intent = await client.cognition.parse_intent("把红色杯子放到桌上")
        plan = await client.decision.execute_plan(intent)

    支持同步 / 异步两种使用方式（取决于各子模块实现）。
    """

    def __init__(self, config: BrainOSConfig | None = None) -> None:
        self._config = config or BrainOSConfig.from_env()
        self._conn = GrpcConnection(self._config)
        self._async_conn = AsyncGrpcConnection(self._config)

        # ── 子模块 ────────────────────────────────────────────
        _ch = self._conn.get_channel
        _ach = self._async_conn.get_channel

        self.cognition = _CognitionNamespace(_ch, _ach, self._config)
        self.decision = _DecisionNamespace(_ch, _ach, self._config)
        self.perception = _PerceptionNamespace(_ch, _ach, self._config)
        self.control = _ControlNamespace(_ch, _ach, self._config)
        self.safety = _SafetyNamespace(_ch, _ach, self._config)
        self.knowledge = _KnowledgeNamespace(_ch, _ach, self._config)
        self.speech = _SpeechNamespace(_ch, _ach, self._config)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "BrainOSClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ── 便捷属性 ──────────────────────────────────────────────

    @property
    def config(self) -> BrainOSConfig:
        return self._config

    def __repr__(self) -> str:
        return (
            f"BrainOSClient(host={self._config.grpc_host!r}, "
            f"port={self._config.grpc_port}, "
            f"robot_id={self._config.robot_id!r})"
        )


# ─────────────────────────────────────────────
# Namespace 代理类（将 API 方法组织到命名空间）
# ─────────────────────────────────────────────

class _CognitionNamespace:
    def __init__(self, ch, ach, cfg):
        self._intent = IntentAPI(ch, ach, cfg)
        self._task = TaskAPI(ch, ach, cfg)

    async def parse_intent(self, utterance: str, language: str = "zh-CN", **kwargs):
        return await self._intent.parse(utterance, language=language, **kwargs)

    async def decompose_task(self, intent, scene_graph=None):
        return await self._task.decompose(intent, scene_graph=scene_graph)

    async def generate_behavior_tree(self, plan_id: str, subtasks):
        return await self._task.generate_bt(plan_id, subtasks)


class _DecisionNamespace:
    def __init__(self, ch, ach, cfg):
        self._plan = PlanAPI(ch, ach, cfg)
        self._traj = TrajectoryAPI(ch, ach, cfg)

    async def execute_plan(self, tree, require_hitl: bool = True):
        return await self._plan.execute(tree, require_hitl=require_hitl)

    async def generate_trajectories(self, plan_id: str, target_pose, num: int = 3):
        return await self._traj.generate(plan_id, target_pose, num_candidates=num)

    async def select_trajectory(self, plan_id: str, trajectory_id: str = ""):
        return await self._traj.select(plan_id, trajectory_id)

    async def cancel_plan(self, plan_id: str, reason: str = ""):
        return await self._plan.cancel(plan_id, reason=reason)


class _PerceptionNamespace:
    def __init__(self, ch, ach, cfg):
        self._scene = SceneAPI(ch, ach, cfg)
        self._object = ObjectAPI(ch, ach, cfg)

    async def get_scene(self, include_summary: bool = False):
        return await self._scene.get(include_summary=include_summary)

    async def query_objects(self, class_label: str = "", min_conf: float = 0.5):
        return await self._object.query(class_label=class_label, min_confidence=min_conf)

    async def get_localization(self):
        return await self._scene.get_localization()


class _ControlNamespace:
    def __init__(self, ch, ach, cfg):
        self._motion = MotionAPI(ch, ach, cfg)
        self._gripper = GripperAPI(ch, ach, cfg)
        self._direct = DirectController(ch, ach, cfg)

    async def execute_trajectory(self, trajectory):
        return await self._motion.execute(trajectory)

    async def emergency_stop(self, reason: str = "", level: int = 0):
        return await self._motion.emergency_stop(reason=reason, level=level)

    async def open_gripper(self):
        return await self._gripper.open()

    async def close_gripper(self, max_effort: float = 10.0):
        return await self._gripper.close(max_effort=max_effort)

    # ── Direct control shortcuts ──────────────────────────
    async def move_joints(self, targets: dict, **kwargs):
        return await self._direct.move_joints(targets, **kwargs)

    async def move_to_pose(self, pose, **kwargs):
        return await self._direct.move_to_pose(pose, **kwargs)

    async def get_state(self):
        return await self._direct.get_state()

    @property
    def direct(self):
        """获取 DirectController 完整访问接口。"""
        return self._direct


class _SafetyNamespace:
    def __init__(self, ch, ach, cfg):
        self._safety = SafetyAPI(ch, ach, cfg)
        self._emergency = EmergencyAPI(ch, ach, cfg)

    async def get_snapshot(self):
        return await self._safety.get_snapshot()

    async def set_velocity_scale(self, scale: float, reason: str = ""):
        return await self._safety.set_velocity_scale(scale, reason=reason)


class _KnowledgeNamespace:
    def __init__(self, ch, ach, cfg):
        self._search = KnowledgeSearchAPI(ch, ach, cfg)
        self._episode = EpisodeAPI(ch, ach, cfg)

    async def search(self, query: str, top_k: int = 5):
        return await self._search.search_knowledge(query, top_k=top_k)

    async def search_episodes(self, query: str, top_k: int = 5):
        return await self._episode.search(query, top_k=top_k)

    async def store_episode(self, episode):
        return await self._episode.store(episode)


class _SpeechNamespace:
    """语音交互命名空间 (ASR + TTS + Voice Command)."""

    def __init__(self, ch, ach, cfg):
        self._speech = SpeechAPI(ch, ach, cfg)

    async def recognize_speech(self, audio, **kwargs):
        return await self._speech.recognize_speech(audio, **kwargs)

    async def synthesize_speech(self, text: str, **kwargs):
        return await self._speech.synthesize_speech(text, **kwargs)

    async def say(self, text: str, **kwargs):
        return await self._speech.say(text, **kwargs)

    async def voice_command(self, audio, **kwargs):
        return await self._speech.voice_command(audio, **kwargs)

    async def listen_for_wake_word(self, wake_words=None, **kwargs):
        return await self._speech.listen_for_wake_word(wake_words=wake_words, **kwargs)

    @property
    def speech(self):
        """获取 SpeechAPI 完整访问接口。"""
        return self._speech
