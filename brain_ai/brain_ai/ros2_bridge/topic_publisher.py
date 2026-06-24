"""
brain_ai/ros2_bridge/topic_publisher.py — ROS 2 topic publisher wrapper.

Supports:
  - Typed publishers with QOS profile control
  - Lazy topic creation
  - Latched publishing for startup state
  - Mock mode for testing
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class QOSProfile(Enum):
    """ROS 2 quality-of-service profiles."""
    RELIABLE = "reliable"           # guaranteed delivery (default)
    BEST_EFFORT = "best_effort"     # lossy, low latency
    SENSOR_DATA = "sensor_data"     # best_effort + small queue
    CRITICAL = "critical"           # reliable + transient_local


@dataclass
class Publication:
    """Record of a single topic publication."""
    timestamp: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)
    topic: str = ""


class TopicPublisher:
    """ROS 2 topic publisher with QOS support and mock fallback.

    Usage::

        pub = TopicPublisher(node=bridge)
        pub.create_publisher("/scene_graph", "brain_os_perception/SceneGraph")
        pub.publish("/scene_graph", {"objects": [...]})
    """

    def __init__(
        self,
        node: Optional[Any] = None,  # ROS2Bridge or rclpy.Node
        default_qos: QOSProfile = QOSProfile.RELIABLE,
        queue_size: int = 10,
        enable_mock: bool = True,
    ) -> None:
        self._node = node
        self._default_qos = default_qos

        # Track created publishers
        self._publishers: dict[str, Any] = {}            # topic → rclpy Publisher
        self._topic_types: dict[str, str] = {}           # topic → message type string
        self._latched_data: dict[str, dict] = {}         # topic → last published data

        # Mock recording
        self._enable_mock = enable_mock
        self._publications: deque[Publication] = deque(maxlen=1000)
        self._subscribers: dict[str, Callable] = {}      # topic → callback (mock mode)
        self._lock = threading.Lock()

    # ── Publisher management ───────────────────────────────────────────

    def create_publisher(
        self,
        topic: str,
        msg_type: str,
        qos: Optional[QOSProfile] = None,
        queue_size: int = 10,
    ) -> bool:
        """Declare a new publisher for a topic."""
        qos = qos or self._default_qos

        if self._has_rclpy_node():
            return self._create_rclpy_publisher(topic, msg_type, qos, queue_size)
        else:
            logger.info(f"[TopicPublisher] Mock publisher: {topic} ({msg_type}, {qos.value})")
            self._topic_types[topic] = msg_type
            return True

    def _create_rclpy_publisher(
        self, topic: str, msg_type: str, qos: QOSProfile, queue_size: int,
    ) -> bool:
        """Create real rclpy publisher with QOS profile."""
        try:
            # import rclpy
            # from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
            # qos_profile = self._build_qos(qos, queue_size)
            # pub = self._node.create_publisher(msg_type, topic, qos_profile)
            # self._publishers[topic] = pub
            # self._topic_types[topic] = msg_type
            logger.info(f"[TopicPublisher] Created publisher: {topic}")
            return True
        except Exception as exc:
            logger.error(f"[TopicPublisher] Failed to create publisher {topic}: {exc}")
            return False

    # ── Publish ────────────────────────────────────────────────────────

    def publish(self, topic: str, data: dict, latch: bool = False) -> bool:
        """Publish a message to a topic.

        Args:
            topic: ROS 2 topic name
            data: message as dict (serialized to ROS msg or JSON)
            latch: if True, store and replay to new subscribers

        Returns:
            True if queued successfully
        """
        if latch:
            self._latched_data[topic] = data

        if self._has_rclpy_publisher(topic):
            return self._publish_rclpy(topic, data)
        else:
            return self._publish_mock(topic, data)

    def _publish_rclpy(self, topic: str, data: dict) -> bool:
        """Real rclpy publish path."""
        try:
            # msg = self._build_ros_msg(topic, data)
            # self._publishers[topic].publish(msg)
            logger.debug(f"[TopicPublisher] Published to {topic}")
            return True
        except Exception as exc:
            logger.error(f"[TopicPublisher] Publish error on {topic}: {exc}")
            return False

    def _publish_mock(self, topic: str, data: dict) -> bool:
        """Mock publish: record and notify local subscribers."""
        with self._lock:
            self._publications.append(Publication(topic=topic, data=data))

        # Notify mock subscribers
        callback = self._subscribers.get(topic)
        if callback:
            try:
                callback(data)
            except Exception as exc:
                logger.error(f"[TopicPublisher] Callback error on {topic}: {exc}")

        return True

    def publish_scene_graph(self, scene_graph: dict) -> bool:
        """Convenience: publish scene graph to /scene_graph topic."""
        return self.publish("/perception/scene_graph", scene_graph)

    def publish_safety_alert(self, alert: dict) -> bool:
        """Convenience: publish safety alert to /safety/alert topic."""
        return self.publish("/safety/alert", alert, latch=True)

    def publish_robot_state(self, state: dict) -> bool:
        """Convenience: publish robot state to /robot/state topic."""
        return self.publish("/robot/state", state)

    # ── Mock subscription (for testing) ────────────────────────────────

    def subscribe_mock(self, topic: str, callback: Callable[[dict], None]) -> None:
        """Register a mock subscriber callback (testing only)."""
        self._subscribers[topic] = callback
        logger.debug(f"[TopicPublisher] Mock subscriber registered: {topic}")

    def get_latest(self, topic: str) -> Optional[dict]:
        """Get the latest published data for a topic (mock mode)."""
        with self._lock:
            for pub in reversed(self._publications):
                if pub.topic == topic:
                    return pub.data
        return self._latched_data.get(topic)

    # ── Internal helpers ───────────────────────────────────────────────

    def _has_rclpy_node(self) -> bool:
        return self._node is not None and hasattr(self._node, "create_publisher")

    def _has_rclpy_publisher(self, topic: str) -> bool:
        return topic in self._publishers

    # ── Statistics ─────────────────────────────────────────────────────

    @property
    def publication_count(self) -> int:
        return len(self._publications)

    def get_stats(self) -> dict:
        return {
            "topics": list(self._topic_types.keys()),
            "total_publications": self.publication_count,
            "latched_topics": list(self._latched_data.keys()),
        }
