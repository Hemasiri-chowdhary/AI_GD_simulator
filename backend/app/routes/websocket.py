"""WebSocket route for real-time GD communication."""
import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

from app.services.session_manager import SessionManager
from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

# Global session manager
session_manager = SessionManager()

# Simple per-connection rate limiting
_rate_limits: dict = {}  # connection_id -> (count, window_start)


@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for GD sessions."""
    await websocket.accept()
    connection_id = id(websocket)
    logger.info(f"🔌 WebSocket connected: {connection_id}")
    
    try:
        # Register connection
        await session_manager.register_connection(websocket, connection_id)
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "payload": {
                "connection_id": str(connection_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        })
        
        # Main message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                logger.debug(f"📨 Received message: {message.get('type')}")
                
                await handle_message(websocket, connection_id, message)
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON format"}
                })
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {connection_id}")
        await session_manager.unregister_connection(connection_id)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await session_manager.unregister_connection(connection_id)
        raise


async def handle_message(websocket: WebSocket, connection_id: int, message: dict):
    """Handle incoming WebSocket messages with rate limiting."""
    # Simple rate limiting: max 30 messages per 10 seconds per connection
    import time
    now = time.monotonic()
    rate_info = _rate_limits.get(connection_id, (0, now))
    count, window_start = rate_info
    if now - window_start > 10:
        count = 0
        window_start = now
    count += 1
    _rate_limits[connection_id] = (count, window_start)
    if count > 30:
        await websocket.send_json({
            "type": "error",
            "payload": {"message": "Rate limit exceeded. Please slow down."}
        })
        return

    msg_type = message.get("type")
    payload = message.get("payload", {})
    
    handlers = {
        "user_join_session": handle_join_session,
        "user_message": handle_user_message,
        "user_select_category": handle_select_category,
        "user_end_session": handle_end_session,
        "session_end": handle_end_session,  # alias for end session
        "session_timer_sync": handle_timer_sync,
        "ping": handle_ping
    }
    
    handler = handlers.get(msg_type)
    if handler:
        await handler(websocket, connection_id, payload)
    else:
        await websocket.send_json({
            "type": "error",
            "payload": {"message": f"Unknown message type: {msg_type}"}
        })


async def handle_join_session(websocket: WebSocket, connection_id: int, payload: dict):
    """Handle user joining a new GD session."""
    category = payload.get("category", "Technology")
    topic = payload.get("topic")
    user_key = payload.get("user_key") or payload.get("user_id")
    duration_minutes = payload.get("duration_minutes", 10)  # Default 10 minutes
    
    # Validate duration (must be 5, 10, 15, or 20 minutes)
    if duration_minutes not in [5, 10, 15, 20]:
        duration_minutes = 10
    
    logger.info(f"👤 User joining session - Category: {category}, Duration: {duration_minutes} min")
    
    session_id = await session_manager.create_session(
        websocket=websocket,
        connection_id=connection_id,
        category=category,
        topic=topic,
        duration_minutes=duration_minutes,
        user_key=user_key
    )
    
    logger.info(f"✅ Session created: {session_id}")


async def handle_user_message(websocket: WebSocket, connection_id: int, payload: dict):
    """Handle user message during GD."""
    content = payload.get("content", "").strip()
    
    if not content:
        return
    
    # Enforce max message length
    max_len = settings.max_message_length
    if len(content) > max_len:
        content = content[:max_len]
    
    logger.info(f"User message: {content[:50]}...")
    
    await session_manager.process_user_message(
        connection_id=connection_id,
        content=content
    )


async def handle_select_category(websocket: WebSocket, connection_id: int, payload: dict):
    """Handle category selection."""
    category = payload.get("category")
    
    await websocket.send_json({
        "type": "category_selected",
        "payload": {"category": category}
    })


async def handle_end_session(websocket: WebSocket, connection_id: int, payload: dict):
    """Handle session end request."""
    logger.info(f"🏁 User ending session")
    
    await session_manager.end_session(connection_id)


async def handle_ping(websocket: WebSocket, connection_id: int, payload: dict):
    """Handle ping message for keepalive."""
    await websocket.send_json({
        "type": "pong",
        "payload": {"timestamp": datetime.now(timezone.utc).isoformat()}
    })


async def handle_timer_sync(websocket: WebSocket, connection_id: int, payload: dict):
    """Handle timer sync request from client."""
    await session_manager.send_timer_snapshot(connection_id)
