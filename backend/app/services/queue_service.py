import json
import logging
from ..celery_app import celery_app
from ..services.event_service import event_service
from ..core.config import settings

logger = logging.getLogger(__name__)

class QueueService:
    @staticmethod
    def get_queue_stats():
        """
        Inspects Celery workers and Redis broker to get comprehensive queue statistics.
        """
        try:
            # 1. Inspect Workers (Active, Reserved, Scheduled)
            inspector = celery_app.control.inspect()

            # These calls can timeout if workers are busy/unresponsive
            # We use a default empty dict if None is returned
            active = inspector.active() or {}
            reserved = inspector.reserved() or {}
            scheduled = inspector.scheduled() or {}

            # 2. Inspect Broker (Redis) for Pending Tasks
            def parse_broker_queue(queue_name: str, limit: int = 50):
                pending_items = []
                try:
                    redis_client = event_service.redis_sync
                    # Redis list name for a queue is usually just the queue name
                    # But Celery defaults might adhere to different naming if not configured.
                    # Based on system.py, it was using just the queue name.
                    raw_items = redis_client.lrange(queue_name, 0, limit - 1)
                    for raw in raw_items:
                        try:
                            message = json.loads(raw)
                            headers = message.get("headers", {}) if isinstance(message, dict) else {}
                            pending_items.append(
                                {
                                    "id": headers.get("id"),
                                    "name": headers.get("task"),
                                    "argsrepr": headers.get("argsrepr"),
                                    "kwargsrepr": headers.get("kwargsrepr"),
                                    "eta": headers.get("eta"),
                                    "queue": queue_name,
                                }
                            )
                        except Exception:
                            pending_items.append({"raw": raw, "queue": queue_name})
                except Exception as exc:
                    logger.warning(f"Failed to inspect broker queue {queue_name}: {exc}")
                return pending_items

            pending = {
                "transcription": parse_broker_queue("transcription"),
                "processing": parse_broker_queue("processing"),
                "maintenance": parse_broker_queue("maintenance"),
                "celery": parse_broker_queue("celery"), # Default queue
            }

            pending_counts = {
                name: len(items) for name, items in pending.items()
            }

            def count_tasks(bucket: dict) -> int:
                return sum(len(tasks) for tasks in bucket.values())

            stats = {
                "workers": list(set(active.keys()) | set(reserved.keys()) | set(scheduled.keys())),
                "active": active,
                "reserved": reserved,
                "scheduled": scheduled,
                # "pending": pending, # Optimization: Don't send full pending list via SSE to save bandwidth
                "counts": {
                    "active": count_tasks(active),
                    "reserved": count_tasks(reserved),
                    "scheduled": count_tasks(scheduled),
                    "total": count_tasks(active) + count_tasks(reserved) + count_tasks(scheduled),
                },
                "pending_counts": pending_counts,
                "pending_total": sum(pending_counts.values()),
                "timestamp": str(event_service.redis_sync.time()[0]) # Server timestamp
            }

            # For the API response (full details), we might want 'pending', but for periodic SSE, maybe not.
            # Let's include it for now as the frontend might use it to list pending items.
            stats["pending"] = pending

            return stats

        except Exception as exc:
            logger.error(f"Failed to inspect queues: {exc}")
            return None
