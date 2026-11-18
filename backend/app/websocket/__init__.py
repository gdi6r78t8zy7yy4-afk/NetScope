# NetScope WebSocket Module

"""
WebSocket handlers for real-time communication.
"""

from app.websocket.manager import ConnectionManager
from app.websocket.events import emit_event

__all__ = ["ConnectionManager", "emit_event"]
