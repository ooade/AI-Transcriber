from enum import Enum
from typing import Dict, Any
import logging
import redis

from .event_service import event_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class ServiceStatus(str, Enum):
    READY = "ready"
    INITIALIZING = "initializing"
    DEGRADED = "degraded"
    ERROR = "error"
    UNAVAILABLE = "unavailable"

class SystemHealthService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemHealthService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.transcriber_status = ServiceStatus.INITIALIZING
        self.transcriber_error = None

        self.llm_status = ServiceStatus.INITIALIZING
        self.llm_error = None

        self.speaker_diarization_status = ServiceStatus.INITIALIZING
        self.speaker_diarization_error = None

        self.last_check = None

    def set_transcriber_status(self, status: ServiceStatus, error: str = None):
        if self.transcriber_status != status:
            logger.info(f"System Health: Transcriber changed from {self.transcriber_status} to {status}")
        self.transcriber_status = status
        self.transcriber_error = error

        # Publish real-time health update
        event_service.publish_event(
            channel="system_status",
            event_type="system_status",
            payload=self.get_status()
        )

    def set_llm_status(self, status: ServiceStatus, error: str = None):
        # Only update and publish if there's an actual change
        if self.llm_status == status and self.llm_error == error:
            return

        logger.info(f"System Health: LLM changed from {self.llm_status} to {status} (Error: {error})")

        self.llm_status = status
        self.llm_error = error

        # Publish real-time health update
        event_service.publish_event(
            channel="system_status",
            event_type="system_status",
            payload=self.get_status()
        )

    def set_speaker_diarization_status(self, status: ServiceStatus, error: str = None):
        """Set speaker diarization service status."""
        if self.speaker_diarization_status != status:
            logger.info(f"System Health: Speaker Diarization changed from {self.speaker_diarization_status} to {status}")
        self.speaker_diarization_status = status
        self.speaker_diarization_error = error

        # Publish real-time health update
        event_service.publish_event(
            channel="system_status",
            event_type="system_status",
            payload=self.get_status()
        )

    def get_status(self) -> Dict[str, Any]:
        overall = ServiceStatus.READY

        if self.transcriber_status == ServiceStatus.ERROR:
            overall = ServiceStatus.ERROR
        elif self.llm_status in [ServiceStatus.ERROR, ServiceStatus.UNAVAILABLE, ServiceStatus.DEGRADED]:
            overall = ServiceStatus.DEGRADED
        elif self.speaker_diarization_status in [ServiceStatus.ERROR]:
            overall = ServiceStatus.DEGRADED
        elif self.transcriber_status == ServiceStatus.INITIALIZING or self.llm_status == ServiceStatus.INITIALIZING or self.speaker_diarization_status == ServiceStatus.INITIALIZING:
            overall = ServiceStatus.INITIALIZING

        # Get task queue depth
        task_queue_depth = self._get_task_queue_depth()

        return {
            "overall_status": overall,
            "components": {
                "transcriber": {
                    "status": self.transcriber_status,
                    "error": self.transcriber_error
                },
                "llm": {
                    "status": self.llm_status,
                    "error": self.llm_error
                },
                "speaker_diarization": {
                    "status": self.speaker_diarization_status,
                    "error": self.speaker_diarization_error
                }
            },
            "task_queue": {
                "transcription_queue_depth": task_queue_depth.get("transcription", 0),
                "processing_queue_depth": task_queue_depth.get("processing", 0),
                "maintenance_queue_depth": task_queue_depth.get("maintenance", 0),
            }
        }

    def _get_task_queue_depth(self) -> Dict[str, int]:
        """Get the depth of Celery task queues."""
        try:
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB_CELERY,
                decode_responses=True
            )
            queues = {
                "transcription": r.llen("celery:celery@transcription"),
                "processing": r.llen("celery:celery@processing"),
                "maintenance": r.llen("celery:celery@maintenance"),
            }
            return queues
        except Exception as e:
            logger.debug(f"Failed to get task queue depth: {e}")
            return {}
