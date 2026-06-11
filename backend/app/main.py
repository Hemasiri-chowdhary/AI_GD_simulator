"""Main FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import websocket_router, api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting AI-GD-Pro Backend...")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("👋 Shutting down AI-GD-Pro Backend...")


app = FastAPI(
    title="AI-GD-Pro",
    description="AI Group Discussion Simulator Backend",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
app.include_router(api_router, prefix="/api", tags=["API"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": "AI-GD-Pro",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check with Ollama connectivity verification."""
    from app.services.ollama_client import OllamaClient
    ollama = OllamaClient()
    ollama_ok = await ollama.check_connection()
    status = "healthy" if ollama_ok else "degraded"
    return {
        "status": status,
        "ollama_url": settings.ollama_base_url,
        "ollama_reachable": ollama_ok,
        "model": settings.ollama_model
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
