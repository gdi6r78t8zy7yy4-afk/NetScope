# NetScope WebSocket Connection Manager

"""
WebSocket connection management for real-time updates.
"""

import asyncio
from typing import Dict, List, Set

from fastapi import WebSocket


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Supports multiple connection types:
    - Scan progress updates
    - Discovery events
    - Vulnerability findings
    """
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "scan": set(),
            "discovery": set(),
            "vulnerability": set(),
            "intelligence": set()
        }
    
    async def connect(self, websocket: WebSocket, channel: str = "scan"):
        """
        Accept a new connection.
        
        Args:
            websocket: WebSocket instance
            channel: Connection type
        """
        await websocket.accept()
        self.active_connections[channel].add(websocket)
    
    async def disconnect(self, websocket: WebSocket, channel: str = "scan"):
        """Remove a connection."""
        if websocket in self.active_connections[channel]:
            self.active_connections[channel].remove(websocket)
    
    async def broadcast_scan_progress(
        self,
        scan_id: int,
        progress: int,
        status: str = "running"
    ):
        """Broadcast scan progress to all connected clients."""
        message = {
            "type": "scan_progress",
            "data": {
                "scan_id": scan_id,
                "progress": progress,
                "status": status
            }
        }
        
        await self._broadcast("scan", message)
    
    async def broadcast_discovery_event(self, event_type: str, data: dict):
        """Broadcast discovery events."""
        message = {
            "type": event_type,
            "data": data
        }
        
        await self._broadcast("discovery", message)
    
    async def broadcast_vulnerability_finding(self, finding: dict):
        """Broadcast new vulnerability findings."""
        message = {
            "type": "vulnerability_finding",
            "data": finding
        }
        
        await self._broadcast("vulnerability", message)
    
    async def broadcast_intelligence_synced(self, source: str, status: str):
        """Broadcast intelligence synchronization events."""
        message = {
            "type": "intelligence_synced",
            "data": {
                "source": source,
                "status": status
            }
        }
        
        await self._broadcast("intelligence", message)
    
    async def _broadcast(self, channel: str, message: dict):
        """Broadcast a message to all connections in a channel."""
        if not self.active_connections[channel]:
            return
        
        disconnected = set()
        
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending message: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            await self.disconnect(conn, channel)


# Global instance
manager = ConnectionManager()
