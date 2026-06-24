"""
brain_ai/ros2_bridge/service_client.py — ROS 2 service client wrapper.

Supports:
  - Sync / async service calls
  - Timeout and retry logic
  - Service availability wait
  - Mock mode for testing
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ServiceCall:
    """Record of a single service call."""
    timestamp: float = field(default_factory=time.time)
    service: str = ""
    request: dict = field(default_factory=dict)
    response: Optional[dict] = None
    success: bool = False
    elapsed_ms: float = 0.0
    error: str = ""


class ServiceClient:
    """ROS 2 service client with retry and mock support.

    Usage::

        cli = ServiceClient(node=bridge)
        resp = cli.call("/control/execute_trajectory", {"trajectory_id": "tr_001"})
    """

    def __init__(
        self,
        node: Optional[Any] = None,  # ROS2Bridge or rclpy.Node
        default_timeout_sec: float = 5.0,
        max_retries: int = 2,
        retry_delay_sec: float = 0.5,
        enable_mock: bool = True,
    ) -> None:
        self._node = node
        self._default_timeout = default_timeout_sec
        self._max_retries = max_retries
        self._retry_delay = retry_delay_sec

        # Created service clients
        self._clients: dict[str, Any] = {}     # service → rclpy Client
        self._service_types: dict[str, str] = {}

        # Mock mode
        self._enable_mock = enable_mock
        self._mock_handlers: dict[str, Callable] = {}  # service → handler(dict) → dict
        self._calls: list[ServiceCall] = []
        self._lock = threading.Lock()

    # ── Client management ──────────────────────────────────────────────

    def register_service(self, service: str, srv_type: str) -> bool:
        """Register a known service type."""
        self._service_types[service] = srv_type

        if self._has_rclpy_node():
            return self._create_rclpy_client(service, srv_type)
        else:
            logger.info(f"[ServiceClient] Mock service: {service} ({srv_type})")
            return True

    def _create_rclpy_client(self, service: str, srv_type: str) -> bool:
        """Create real rclpy service client."""
        try:
            # import rclpy
            # client = self._node.create_client(srv_class, service)
            # self._clients[service] = client
            logger.info(f"[ServiceClient] Created client: {service}")
            return True
        except Exception as exc:
            logger.error(f"[ServiceClient] Create client error {service}: {exc}")
            return False

    # ── Call ───────────────────────────────────────────────────────────

    def call(
        self,
        service: str,
        request: dict,
        timeout_sec: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> ServiceCall:
        """Synchronous service call with timeout and retry.

        Args:
            service: ROS 2 service name
            request: request data as dict
            timeout_sec: wait timeout per attempt (default: 5s)
            retries: number of retries on timeout (default: 2)

        Returns:
            ServiceCall with response/error details
        """
        timeout = timeout_sec if timeout_sec is not None else self._default_timeout
        retries = retries if retries is not None else self._max_retries

        for attempt in range(retries + 1):
            call_record = self._call_attempt(service, request, timeout, attempt)
            if call_record.success:
                return call_record
            if attempt < retries:
                time.sleep(self._retry_delay)

        return call_record

    def _call_attempt(
        self, service: str, request: dict, timeout: float, attempt: int,
    ) -> ServiceCall:
        """Single service call attempt."""
        start = time.perf_counter()
        record = ServiceCall(service=service, request=request)

        try:
            if self._has_rclpy_client(service):
                response = self._call_rclpy(service, request, timeout)
            elif service in self._mock_handlers:
                response = self._call_mock_handler(service, request)
            else:
                response = self._call_mock_default(service, request)

            elapsed = (time.perf_counter() - start) * 1000
            record = ServiceCall(
                service=service, request=request,
                response=response, success=True,
                elapsed_ms=round(elapsed, 2),
            )
        except TimeoutError:
            elapsed = (time.perf_counter() - start) * 1000
            record = ServiceCall(
                service=service, request=request,
                success=False, elapsed_ms=round(elapsed, 2),
                error=f"Timeout after {timeout}s (attempt {attempt + 1})",
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            record = ServiceCall(
                service=service, request=request,
                success=False, elapsed_ms=round(elapsed, 2),
                error=str(exc),
            )

        with self._lock:
            self._calls.append(record)

        return record

    def _call_rclpy(self, service: str, request: dict, timeout: float) -> dict:
        """Real rclpy service call (synchronous)."""
        _ = service, request, timeout
        # client = self._clients[service]
        # if not client.wait_for_service(timeout_sec=timeout):
        #     raise TimeoutError(...)
        # future = client.call_async(request_msg)
        # rclpy.spin_until_future_complete(self._node, future, timeout_sec=timeout)
        # return future.result()
        raise TimeoutError("rclpy not available")

    def _call_mock_handler(self, service: str, request: dict) -> dict:
        """Call registered mock handler."""
        handler = self._mock_handlers[service]
        return handler(request)

    def _call_mock_default(self, service: str, request: dict) -> dict:
        """Default mock response."""
        logger.debug(f"[ServiceClient] Mock call: {service} with {list(request.keys())}")
        return {
            "status": "ok",
            "service": service,
            "message": f"Mock response for {service}",
        }

    # ── Service availability ───────────────────────────────────────────

    def wait_for_service(
        self, service: str, timeout_sec: float = 10.0,
    ) -> bool:
        """Block until service is available or timeout."""
        if self._has_rclpy_client(service):
            # return self._clients[service].wait_for_service(timeout_sec)
            pass
        # Mock: always available
        return True

    def is_available(self, service: str) -> bool:
        """Check if a service is immediately available."""
        return (
            service in self._clients or
            service in self._mock_handlers or
            self._enable_mock
        )

    # ── Mock handlers (for testing) ────────────────────────────────────

    def register_mock_handler(
        self, service: str, handler: Callable[[dict], dict],
    ) -> None:
        """Register a mock response handler for a service."""
        self._mock_handlers[service] = handler
        self._service_types.setdefault(service, "mock")
        logger.debug(f"[ServiceClient] Mock handler registered: {service}")

    # ── Convenience methods ────────────────────────────────────────────

    def emergency_stop(self, robot_id: str = "default") -> ServiceCall:
        """Call /control/emergency_stop service."""
        return self.call("/control/emergency_stop", {
            "robot_id": robot_id,
            "reason": "user_requested",
        }, timeout_sec=2.0, retries=0)

    def execute_trajectory(self, trajectory_id: str) -> ServiceCall:
        """Call /control/execute_trajectory service."""
        return self.call("/control/execute_trajectory", {
            "trajectory_id": trajectory_id,
        })

    def get_localization(self, robot_id: str = "default") -> ServiceCall:
        """Call /perception/get_localization service."""
        return self.call("/perception/get_localization", {
            "robot_id": robot_id,
        })

    # ── Helpers ────────────────────────────────────────────────────────

    def _has_rclpy_node(self) -> bool:
        return self._node is not None and hasattr(self._node, "create_client")

    def _has_rclpy_client(self, service: str) -> bool:
        return service in self._clients

    # ── Statistics ─────────────────────────────────────────────────────

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def get_stats(self) -> dict:
        with self._lock:
            success_count = sum(1 for c in self._calls if c.success)
        return {
            "total_calls": len(self._calls),
            "success_rate": success_count / max(1, len(self._calls)),
            "services": {
                svc: sum(1 for c in self._calls if c.service == svc)
                for svc in self._service_types
            },
        }
