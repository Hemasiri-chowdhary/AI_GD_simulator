"""API Routes."""
from app.routes.websocket import router as websocket_router
from app.routes.api import router as api_router

__all__ = ["websocket_router", "api_router"]
