import json
import redis
import redis.asyncio as aioredis
import logging
from typing import AsyncGenerator, Any
from ..core.config import settings

logger = logging.getLogger(__name__)

class EventService:
    def __init__(self):
        # Sync client for Celery tasks
        self.redis_sync = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB_CELERY, # Use a dedicated DB or the same? Celery uses 0. Let's use 0 for Pub/Sub too or separate?
            # PubSub is DB-agnostic in Redis Cluster but in standalone it matters less.
            # Let's use DB 0 for simplicity.
            decode_responses=True
        )

        # Async connection URL
        self.redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB_CELERY}"

    def publish_event(self, channel: str, event_type: str, payload: dict):
        """
        Publish an event to a Redis channel.
        Safe to call from synchronous Celery workers.
        """
        try:
            message = json.dumps({
                "type": event_type,
                "payload": payload
            })
            self.redis_sync.publish(channel, message)
            logger.debug(f"Published event {event_type} to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")

    async def stream_events(self, channel_pattern: str = "*") -> AsyncGenerator[str, None]:
        """
        Subscribe to Redis channels and yield SSE-formatted messages.
        Safe to call from async FastAPI endpoints.
        """
        client = aioredis.from_url(self.redis_url, decode_responses=True)
        pubsub = client.pubsub()

        try:
            # Subscribe to the channel (or pattern)
            # We use psubscribe to listen to specific task IDs or global events
            await pubsub.psubscribe(channel_pattern)

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    data = message["data"]
                    # Format as Server-Sent Event
                    # SSE format: "data: <content>\n\n"
                    yield f"data: {data}\n\n"

        except Exception as e:
            logger.error(f"SSE Stream Error: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"
        finally:
            await pubsub.unsubscribe()
            await client.close()

# Global event service instance
event_service = EventService()
