"""WebSocket endpoints for real-time updates."""
import asyncio
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger()
router = APIRouter()

# Connection managers for different channels
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info("WebSocket disconnected", total_connections=len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected.add(connection)

        # Clean up disconnected clients
        self.active_connections -= disconnected

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        """Send message to specific client."""
        await websocket.send_json(message)


# Global connection managers
updates_manager = ConnectionManager()
settings_manager = ConnectionManager()


@router.websocket("/updates")
async def websocket_updates(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time agent updates."""
    await updates_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle subscription requests
            if message.get("type") == "subscribe":
                await updates_manager.send_personal(
                    websocket,
                    {"type": "subscribed", "channel": message.get("channel", "all")}
                )
            elif message.get("type") == "ping":
                await updates_manager.send_personal(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        updates_manager.disconnect(websocket)


@router.websocket("/settings")
async def websocket_settings(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time settings changes."""
    await settings_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await settings_manager.send_personal(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        settings_manager.disconnect(websocket)


async def broadcast_agent_update(agent_id: str, status: str, data: dict) -> None:
    """Broadcast agent status update to all connected clients."""
    await updates_manager.broadcast({
        "type": "agent_update",
        "agent_id": agent_id,
        "status": status,
        "data": data,
    })


async def broadcast_settings_change(category: str, key: str, value: str) -> None:
    """Broadcast settings change to all connected clients."""
    await settings_manager.broadcast({
        "type": "settings_changed",
        "category": category,
        "key": key,
        "value": value,
    })
