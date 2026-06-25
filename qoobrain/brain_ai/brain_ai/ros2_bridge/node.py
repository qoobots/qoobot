"""
brain_ai/ros2_bridge/ — ROS 2 bridge for brain_ai (Python).

Provides:
  - ROS 2 node lifecycle
  - Topic publisher/subscriber
  - Service client
  - Integration with brain_core topics
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ROS2Bridge:
    """Unified ROS 2 bridge for brain_ai Python modules.

    Sprint 1: Stub for connectivity verification.
    Real impl: uses rclpy for ROS 2 communication.
    """

    def __init__(self, node_name: str = "brain_ai_bridge"):
        self._node_name = node_name
        logger.info(f"[ROS2Bridge] Initialized node: {node_name}")

    def start(self) -> None:
        """Initialize rclpy and create node."""
        logger.info(f"[ROS2Bridge] Starting node: {self._node_name}")
        # Real impl: rclpy.init(); node = rclpy.create_node(self._node_name)

    def stop(self) -> None:
        """Shutdown ROS 2 node."""
        logger.info("[ROS2Bridge] Stopping node")
        # Real impl: node.destroy_node(); rclpy.shutdown()

    def publish(self, topic: str, data: dict) -> bool:
        """Publish a message to a ROS 2 topic.

        Args:
            topic: ROS 2 topic name
            data: serializable dict

        Returns:
            True if published successfully
        """
        logger.info(f"[ROS2Bridge] Publishing to {topic}: {data}")
        return True

    def subscribe(self, topic: str, callback) -> bool:
        """Subscribe to a ROS 2 topic.

        Args:
            topic: ROS 2 topic name
            callback: function(msg) called on each message

        Returns:
            True if subscribed successfully
        """
        logger.info(f"[ROS2Bridge] Subscribed to {topic}")
        return True

    def call_service(self, service: str, request: dict, timeout_sec: float = 5.0) -> dict:
        """Call a ROS 2 service.

        Args:
            service: service name
            request: request dict
            timeout_sec: timeout in seconds

        Returns:
            Response dict
        """
        logger.info(f"[ROS2Bridge] Calling service {service}")
        return {"status": "ok"}
