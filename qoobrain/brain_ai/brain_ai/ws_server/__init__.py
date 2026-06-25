"""
brain_ai/ws_server — WebSocket server for brain_viz communication.

Modules:
  - ws_handler:         WebSocket server (websockets library)
  - event_dispatcher:   Internal event bus → WebSocket bridge
"""

from brain_ai.ws_server.ws_handler import WSServer, get_ws_server
from brain_ai.ws_server.event_dispatcher import EventDispatcher, EventPriority, DomainEvent, get_event_dispatcher

__all__ = [
    "WSServer",
    "get_ws_server",
    "EventDispatcher",
    "EventPriority",
    "DomainEvent",
    "get_event_dispatcher",
]
