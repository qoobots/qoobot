"""
brain_ai/grpc_server/server.py — Main gRPC server for brain_ai.

Exposes:
  - CognitionService:  intent parsing, task decomposition, BT generation
  - DecisionService:  trajectory generation, HITL management
  - KnowledgeService: working memory, experience retrieval
  - PerceptionService: scene graph, localization, object query

Communicates with:
  - brain_core  via gRPC client (control, perception, safety)
  - brain_viz   via WebSocket (scene updates, ghost trails)
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from concurrent import futures

import grpc

from brain_ai.grpc_server.cognition_service import CognitionServiceServicer
from brain_ai.grpc_server.decision_service import DecisionServiceServicer
from brain_ai.grpc_server.knowledge_service import KnowledgeServiceServicer
from brain_ai.grpc_server.perception_service import PerceptionServiceServicer

logger = logging.getLogger(__name__)


class BrainAIGrpcServer:
    """Main gRPC server hosting all brain_ai services."""

    def __init__(
        self,
        listen_address: str = "0.0.0.0:50052",
        max_workers: int = 10,
        max_message_mb: int = 16,
    ):
        self._address = listen_address
        self._max_workers = max_workers
        self._max_msg_len = max_message_mb * 1024 * 1024
        self._server: grpc.Server | None = None

        # Service instances
        self.cognition_servicer = CognitionServiceServicer()
        self.decision_servicer = DecisionServiceServicer()
        self.knowledge_servicer = KnowledgeServiceServicer()
        self.perception_servicer = PerceptionServiceServicer()

    def start(self) -> None:
        """Start the gRPC server (non-blocking)."""
        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self._max_workers),
            options=[
                ("grpc.max_send_message_length", self._max_msg_len),
                ("grpc.max_receive_message_length", self._max_msg_len),
                ("grpc.keepalive_time_ms", 30000),
                ("grpc.keepalive_timeout_ms", 10000),
            ],
        )

        # Register all services
        from brain_ai.proto_gen.brain_os.cognition import service_pb2_grpc
        from brain_ai.proto_gen.brain_os.decision import service_pb2_grpc
        from brain_ai.proto_gen.brain_os.knowledge import service_pb2_grpc
        from brain_ai.proto_gen.brain_os.perception import service_pb2_grpc

        service_pb2_grpc.add_CognitionServiceServicer_to_server(
            self.cognition_servicer, self._server,
        )
        service_pb2_grpc.add_DecisionServiceServicer_to_server(
            self.decision_servicer, self._server,
        )
        service_pb2_grpc.add_KnowledgeServiceServicer_to_server(
            self.knowledge_servicer, self._server,
        )
        service_pb2_grpc.add_PerceptionServiceServicer_to_server(
            self.perception_servicer, self._server,
        )

        self._server.add_insecure_port(self._address)
        self._server.start()
        logger.info(f"[BrainAIGrpcServer] gRPC server listening on {self._address}")

    def stop(self, grace_sec: float = 5.0) -> None:
        """Gracefully stop the gRPC server."""
        if self._server:
            logger.info("[BrainAIGrpcServer] Shutting down...")
            self._server.stop(grace_sec)
            logger.info("[BrainAIGrpcServer] Stopped.")

    def wait_for_termination(self) -> None:
        """Block until the server terminates."""
        if self._server:
            self._server.wait_for_termination()


# ── Entry points ──────────────────────────────────────────────────────────

def serve_blocking(address: str = "0.0.0.0:50052") -> None:
    """Blocking entry point — starts server and waits for SIGINT/SIGTERM."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s %(levelname)s] %(name)s: %(message)s",
    )

    server = BrainAIGrpcServer(listen_address=address)
    server.start()

    # Handle shutdown signals
    stop_event = threading.Event()

    def _signal_handler(sig, frame):
        logger.info(f"[brain_ai] Received signal {sig}, shutting down...")
        server.stop()
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info(f"[brain_ai] gRPC server running at {address} — Ctrl+C to stop")
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="brain_ai gRPC server")
    parser.add_argument(
        "--address", default="0.0.0.0:50052",
        help="gRPC listen address (default: 0.0.0.0:50052)",
    )
    args = parser.parse_args()
    serve_blocking(address=args.address)
