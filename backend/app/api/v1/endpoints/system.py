import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from celery.result import AsyncResult
from sqlalchemy.orm import Session
from ....core.config import settings
from ....services.health_service import SystemHealthService, ServiceStatus
from ....services.event_service import event_service
from ....services.accuracy_service import AccuracyService
from ....database import get_db
from ....celery_app import celery_app
from .... import schemas

# Create a logger (structlog will intercept this if configured)
logger = logging.getLogger(__name__)

router = APIRouter()
health_service = SystemHealthService()

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/queues")
@router.get("/queues")
def get_queues():
    from ....services.queue_service import QueueService
    stats = QueueService.get_queue_stats()
    if not stats:
        raise HTTPException(status_code=500, detail="Failed to inspect queues")
    return stats

@router.post("/queues/revoke/{task_id}")
def revoke_task(task_id: str):
    try:
        celery_app.control.revoke(task_id, terminate=False)
        return {"ok": True, "task_id": task_id, "action": "revoked"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to revoke task: {exc}")

@router.post("/queues/purge")
def purge_queues():
    try:
        purged = celery_app.control.purge()
        return {"ok": True, "purged": purged}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to purge queues: {exc}")

@router.get("/system/status")
async def system_status():
    """Returns the granular health status of all subsystems."""
    return health_service.get_status()

@router.get("/system/transcription-backends")
async def get_transcription_backends():
    """
    Returns available transcription backends with their capabilities.

    Returns:
        Dict with backend info including availability, acceleration type, and supported models.
    """
    from ....tasks import transcriber_cache

    backends = transcriber_cache.get_available_backends()

    # Add preloaded models info
    preloaded_models = [m.strip() for m in settings.PRELOAD_MODELS.split(",") if m.strip()]

    return {
        "backends": backends,
        "default_backend": settings.WHISPER_BACKEND,
        "default_model": settings.WHISPER_MODEL_SIZE,
        "preloaded_models": preloaded_models,
        "model_info": {
            "tiny": {"speed": "10x faster", "accuracy": "70%", "description": "Ultra-fast, lower accuracy"},
            "base": {"speed": "5x faster", "accuracy": "85%", "description": "Fast with good accuracy"},
            "small": {"speed": "3x faster", "accuracy": "90%", "description": "Balanced speed and accuracy"},
            "medium": {"speed": "2x faster", "accuracy": "95%", "description": "High accuracy, moderate speed"},
            "large-v3": {"speed": "1x (baseline)", "accuracy": "99%", "description": "Highest accuracy, slowest"}
        }
    }

@router.get("/system/insights", response_model=schemas.InsightData)
async def get_insights(db: Session = Depends(get_db)):
    """Returns analytics and improvement metrics."""
    accuracy = AccuracyService(db)
    return accuracy.get_global_metrics()

# SSE Endpoint
@router.get("/events")
async def events_stream(request: Request, task_id: Optional[str] = None):
    """
    Server-Sent Events (SSE) endpoint.
    Streams real-time updates for tasks using Redis Pub/Sub.
    If task_id is provided, pushes the current status immediately.
    """

    async def event_generator():
        # 0. Push current system status immediately (Hydration)
        try:
            status_data = {
                "type": "system_status",
                "payload": health_service.get_status()
            }
            yield f"data: {json.dumps(status_data)}\n\n"
        except Exception as e:
            logger.error(f"Failed to push initial SSE system status: {e}")

        # 1. If task_id provided, push initial state immediately (Hydration)
        if task_id:
            try:
                result = AsyncResult(task_id)
                initial_data = {
                    "type": "task_progress",
                    "payload": {
                        "task_id": task_id,
                        "status": result.status,
                        "progress_stage": "initialized" if result.status == "PENDING" else "discovered",
                        "message": "Initializing tracking..." if result.status == "PENDING" else "Re-syncing task..."
                    }
                }
                yield f"data: {json.dumps(initial_data)}\n\n"
            except Exception as e:
                logger.error(f"Failed to push initial SSE task status: {e}")

        # 2. Start streaming Redis events
        async for event in event_service.stream_events(channel_pattern="app:*"):
            # Check for client disconnection
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.get("/tasks/{task_id}", response_model=schemas.TaskStatusResponse)
async def get_task_status(task_id: str):
    """Poll the status of a background job."""
    try:
        result = AsyncResult(task_id)

        # Safely serialize the error
        error_msg = None
        if result.failed():
            try:
                error_msg = str(result.info)
            except Exception:
                error_msg = "Task failed with unknown error"

        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() and not result.failed() else None,
            "error": error_msg
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "UNKNOWN",
            "result": None,
            "error": f"Failed to get task status: {str(e)}"
        }
