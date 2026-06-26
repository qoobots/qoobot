"""
Communication API - ROS 2 bridge and gRPC client interfaces.

Provides high-level interfaces for communicating with the
QooBot Brain OS runtime.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, Any

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for connecting to Brain OS.

    Attributes:
        host: gRPC server hostname
        grpc_port: gRPC port
        ws_port: WebSocket port
        use_tls: Whether to use TLS
        timeout: Connection timeout in seconds
    """
    host: str = "localhost"
    grpc_port: int = 50052
    ws_port: int = 8765
    use_tls: bool = False
    timeout: float = 10.0


class BrainOSClient:
    """Client for communicating with Brain OS runtime.

    Provides high-level APIs for perception, control, and knowledge services.

    Example:
        client = BrainOSClient(ConnectionConfig(host="192.168.1.100"))
        await client.connect()
        scene = await client.perception.get_scene()
        await client.control.move_joints({"arm_1": 0.5})
        await client.disconnect()
    """

    def __init__(self, config: Optional[ConnectionConfig] = None):
        self.config = config or ConnectionConfig()
        self._connected = False

    async def connect(self) -> None:
        """Connect to the Brain OS runtime."""
        logger.info(
            f"Connecting to Brain OS at {self.config.host}:{self.config.grpc_port}"
        )
        # TODO: Implement gRPC connection
        self._connected = True
        logger.info("Connected to Brain OS")

    async def disconnect(self) -> None:
        """Disconnect from the Brain OS runtime."""
        self._connected = False
        logger.info("Disconnected from Brain OS")

    @property
    def is_connected(self) -> bool:
        """Whether the client is connected."""
        return self._connected

    async def health_check(self) -> bool:
        """Check if the Brain OS runtime is healthy."""
        return self._connected  # TODO: actual health check


class ROS2Bridge:
    """Bridge for ROS 2 communication.

    Provides publish/subscribe interfaces for ROS 2 topics.

    Example:
        bridge = ROS2Bridge()
        await bridge.connect()
        await bridge.subscribe("/camera/rgb", on_image)
        await bridge.publish("/cmd_vel", twist_msg)
    """

    def __init__(self, namespace: str = ""):
        self.namespace = namespace
        self._connected = False
        self._subscribers: dict = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()

    async def connect(self) -> None:
        """Initialize ROS 2 bridge."""
        logger.info("Initializing ROS 2 bridge...")
        # TODO: Implement actual ROS 2 DDS bridge
        self._connected = True
        logger.info("ROS 2 bridge initialized")

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[Any], Awaitable[None]],
        msg_type: str = "",
    ) -> None:
        """Subscribe to a ROS 2 topic.

        Args:
            topic: Topic name (e.g., "/camera/rgb")
            callback: Async callback for received messages
            msg_type: ROS 2 message type string
        """
        full_topic = f"{self.namespace}/{topic.lstrip('/')}"
        logger.info(f"Subscribing to {full_topic}")
        self._subscribers[full_topic] = callback
        # TODO: Actual DDS subscription

    async def publish(self, topic: str, msg: Any) -> None:
        """Publish a message to a ROS 2 topic.

        Args:
            topic: Topic name
            msg: Message to publish
        """
        full_topic = f"{self.namespace}/{topic.lstrip('/')}"
        # TODO: Actual DDS publication
        logger.debug(f"Publishing to {full_topic}")

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic."""
        full_topic = f"{self.namespace}/{topic.lstrip('/')}"
        self._subscribers.pop(full_topic, None)
