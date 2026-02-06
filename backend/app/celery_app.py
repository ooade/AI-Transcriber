import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

# Redis configuration with fallback to REDIS_HOST/REDIS_PORT
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    REDIS_URL = f"redis://{redis_host}:{redis_port}"

BROKER_URL = f"{REDIS_URL}/0"
RESULT_BACKEND = f"{REDIS_URL}/1"

# ⚠️ CRITICAL: SQLite broker is NOT suitable for production
# Limitations:
# - Single worker only (no distributed processing)
# - No transaction guarantees for task state
# - File locking issues under concurrent load
# - No task routing or priority queues
# Only use for local development with a single worker instance
if os.getenv("USE_SQLITE_BROKER") == "true":
    logger.warning(
        "⚠️  USING SQLITE BROKER - DEV ONLY MODE ⚠️\n"
        "   This configuration is NOT suitable for production.\n"
        "   Run only ONE worker instance to avoid database locking.\n"
        "   Redis is required for production deployments."
    )
    BROKER_URL = "sqla+sqlite:///./temp/celery_broker.db"
    RESULT_BACKEND = "db+sqlite:///./temp/celery_results.db"

celery_app = Celery(
    "worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max
    task_acks_late=True,
    worker_prefetch_multiplier=1, # One task per worker at a time for Whisper concurrency

    # Task routing: separate queues for different task priorities
    task_routes={
        'app.tasks.transcribe_audio_task': {'queue': 'transcription', 'routing_key': 'transcription.#'},
        'app.tasks.run_auto_correct_task': {'queue': 'processing', 'routing_key': 'processing.#'},
        'app.tasks.generate_summary_task': {'queue': 'processing', 'routing_key': 'processing.#'},
        'app.tasks.clean_stale_audio_task': {'queue': 'maintenance', 'routing_key': 'maintenance.#'},
    },

    # Reject tasks that can't be deserialized (corrupted messages)
    task_reject_on_worker_lost=True,

    # Task event states (needed for monitoring)
    task_send_sent_event=True,

    # Periodic Tasks
    beat_schedule={
        "cleanup-stale-audio": {
            "task": "app.tasks.clean_stale_audio_task",
            "schedule": 3600 * 6, # Every 6 hours
        },
        "broadcast-queue-stats": {
            "task": "app.tasks.broadcast_queue_stats_task",
            "schedule": 3.0, # Every 3 seconds
        },
    },
)

# Optional: Auto-discover tasks in the 'app' package
celery_app.autodiscover_tasks(['app'])
