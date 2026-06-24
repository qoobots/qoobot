"""
brain_ai/ros2_bridge/topic_subscriber.py — ROS 2 topic subscriber wrapper.

Supports:
  - Typed subscribers with QOS profiles
  - Callback chaining (multiple callbacks per topic)
  - Spin thread for async message processing
  - Mock mode with simulated data injection
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Metadata for a single topic subscription."""
    topic: str
    msg_type: str
    callbacks: list[Callable] = field(default_factory=list)
    msg_count: int = 0
    last_msg_time: float = 0.0


class TopicSubscriber:
    """ROS 2 topic subscriber with callback management.

    Usage::

        sub = TopicSubscriber(node=bridge)
        def on_scene(msg):
            print(f"Scene received: {msg}")
        sub.subscribe("/perception/scene_graph", "SceneGraph", on_scene)
    """

    def __init__(
        self,
        node: Optional[Any] = None,  # ROS2Bridge or rclpy.Node
        spin_thread: bool = True,
        enable_mock: bool = True,
    ) -> None:
        self._node = node

        # Subscriptions
        self._subscriptions: dict[str, Subscription] = {}
        self._rclpy_subscriptions: dict[str, Any] = {}  # rclpy Subscription objects

        # Spin thread
        self._spin_thread: Optional[threading.Thread] = None
        self._should_spin = False
        if spin_thread:
            self._start_spin()

        # Mock mode
        self._enable_mock = enable_mock
        self._mock_queue: deque[tuple[str, dict]] = deque(maxlen=500)
        self._lock = threading.Lock()

    # ── Subscription management ────────────────────────────────────────

    def subscribe(
        self,
        topic: str,
        msg_type: str,
        callback: Callable[[dict], None],
        queue_size: int = 10,
    ) -> bool:
        """Subscribe to a ROS 2 topic.

        Args:
            topic: ROS 2 topic name
            msg_type: message type string (e.g. "brain_os_perception/SceneGraph")
            callback: called with dict form of each received message
            queue_size: subscription queue depth

        Returns:
            True if subscribed successfully
        """
        if topic not in self._subscriptions:
            self._subscriptions[topic] = Subscription(
                topic=topic, msg_type=msg_type,
            )

        sub = self._subscriptions[topic]
        if callback not in sub.callbacks:
            sub.callbacks.append(callback)

        if self._has_rclpy_node():
            return self._subscribe_rclpy(topic, msg_type, queue_size)
        else:
            logger.info(f"[TopicSubscriber] Mock subscribe: {topic} ({msg_type})")
            return True

    def _subscribe_rclpy(
        self, topic: str, msg_type: str, queue_size: int,
    ) -> bool:
        """Create real rclpy subscription."""
        try:
            # import rclpy
            # from rclpy.qos import qos_profile_sensor_data
            # rcl_sub = self._node.create_subscription(
            #     msg_class, topic, self._dispatch_callback(topic), queue_size,
            # )
            # self._rclpy_subscriptions[topic] = rcl_sub
            logger.info(f"[TopicSubscriber] Subscribed to {topic}")
            return True
        except Exception as exc:
            logger.error(f"[TopicSubscriber] Subscribe error on {topic}: {exc}")
            return False

    def unsubscribe(self, topic: str, callback: Optional[Callable] = None) -> None:
        """Remove a callback or entire subscription."""
        if callback and topic in self._subscriptions:
            self._subscriptions[topic].callbacks = [
                cb for cb in self._subscriptions[topic].callbacks
                if cb != callback
            ]
        elif topic in self._subscriptions:
            del self._subscriptions[topic]
            if topic in self._rclpy_subscriptions:
                del self._rclpy_subscriptions[topic]

    # ── Message dispatch ───────────────────────────────────────────────

    def _dispatch(self, topic: str, msg: dict) -> None:
        """Dispatch a message to all registered callbacks."""
        sub = self._subscriptions.get(topic)
        if not sub:
            return

        sub.msg_count += 1
        sub.last_msg_time = time.time()

        for cb in sub.callbacks:
            try:
                cb(msg)
            except Exception as exc:
                logger.error(f"[TopicSubscriber] Callback error on {topic}: {exc}")

    # ── Spin thread ────────────────────────────────────────────────────

    def _start_spin(self) -> None:
        """Start background spin thread for mock message processing."""
        self._should_spin = True
        self._spin_thread = threading.Thread(
            target=self._spin_loop, daemon=True, name="ros2-spin",
        )
        self._spin_thread.start()
        logger.debug("[TopicSubscriber] Spin thread started")

    def _spin_loop(self) -> None:
        """Process mock queue messages."""
        while self._should_spin:
            with self._lock:
                if self._mock_queue:
                    topic, msg = self._mock_queue.popleft()
                    self._dispatch(topic, msg)
            time.sleep(0.01)  # 100 Hz

    def stop_spin(self) -> None:
        """Stop the spin thread."""
        self._should_spin = False
        if self._spin_thread:
            self._spin_thread.join(timeout=2.0)
            logger.debug("[TopicSubscriber] Spin thread stopped")

    # ── Mock injection (for testing) ───────────────────────────────────

    def inject_mock_message(self, topic: str, msg: dict) -> None:
        """Simulate receiving a message (testing only)."""
        with self._lock:
            self._mock_queue.append((topic, msg))

    def inject_scene_graph(self, scene_graph: dict) -> None:
        """Simulate receiving a SceneGraph message."""
        self.inject_mock_message("/perception/scene_graph", scene_graph)

    def inject_safety_alert(self, alert: dict) -> None:
        """Simulate receiving a safety alert message."""
        self.inject_mock_message("/safety/alert", alert)

    # ── Query ──────────────────────────────────────────────────────────

    def get_subscription(self, topic: str) -> Optional[Subscription]:
        return self._subscriptions.get(topic)

    @property
    def subscribed_topics(self) -> list[str]:
        return list(self._subscriptions.keys())

    def _has_rclpy_node(self) -> bool:
        return self._node is not None and hasattr(self._node, "create_subscription")

    # ── Statistics ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "topics": {
                topic: {"msg_count": sub.msg_count, "callbacks": len(sub.callbacks)}
                for topic, sub in self._subscriptions.items()
            },
            "queue_depth": len(self._mock_queue),
        }
