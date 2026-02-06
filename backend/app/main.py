import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import Core modules
from .core.config import settings
from .core.logging import configure_logging
from .middleware.correlation import CorrelationIdMiddleware

# Import Services for Startup checks
from .services.context_service import ContextService
from .services.health_service import SystemHealthService, ServiceStatus
from .database import engine
from . import models

# Import Routers
from .api.v1.endpoints import transcription, system, history, speakers

# Configure Logging (JSON + Structlog)
configure_logging(log_level="INFO", json_format=True)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Transcriber API")

# Middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directory exists
os.makedirs("temp", exist_ok=True)

# Include Routers
# NOTE: We mount at root for backward compatibility.
# Future: Mount under /api/v1 prefix.
app.include_router(transcription.router, tags=["transcription"])
app.include_router(system.router, tags=["system"])
app.include_router(history.router, tags=["history"])
app.include_router(speakers.router, tags=["speakers"])

# Global Services
context_service = ContextService()
health_service = SystemHealthService()

@app.on_event("startup")
async def startup_event():
    """Application Startup: Warmup models and check connections."""
    logger.info("🚀 Starting Backend Services...")

    # 0. Check Redis Connection (Required for SSE/Celery)
    try:
        from .services.event_service import event_service
        # Test Redis connection
        event_service.redis_sync.ping()
        logger.info("✅ Redis Connected")
    except Exception as e:
        if settings.REDIS_REQUIRED or settings.ENVIRONMENT == "production":
            logger.error(f"❌ FATAL: Redis connection failed in production mode: {e}")
            raise SystemExit(1)
        else:
            logger.warning(f"⚠️  Redis Unavailable: {e}")

    # 1. Initialize Transcriber (Critical Dependency)
    try:
        health_service.set_transcriber_status(ServiceStatus.INITIALIZING)

        # Trigger cache initialization (preloads models)
        from .tasks import transcriber_cache
        # Running in thread to avoid blocking loop if it does heavy I/O
        await asyncio.to_thread(transcriber_cache.initialize)

        health_service.set_transcriber_status(ServiceStatus.READY)
        logger.info("✅ Transcriber Ready (Cache Initialized)")
    except Exception as e:
        logger.error(f"❌ Transcriber Failed: {e}")
        health_service.set_transcriber_status(ServiceStatus.ERROR, str(e))

    # 2. Initialize Ollama (Optional Dependency)
    logger.info("Checking Ollama Connection...")
    try:
        is_connected = await context_service.check_connection()
        if is_connected:
            logger.info("✅ Ollama Connected")
        else:
            logger.warning("⚠️  Ollama Unavailable - Running in DEGRADED mode (Transcription Only)")
    except Exception as e:
        logger.warning(f"⚠️  Ollama Check Failed: {e} - Running in DEGRADED mode (Transcription Only)")
