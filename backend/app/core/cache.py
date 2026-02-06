import json
import logging
import hashlib
import functools
import inspect
import asyncio
from typing import Any, Optional, Protocol, Union, Callable, TypeVar, Awaitable
import redis
import redis.asyncio as aredis

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CacheProvider(Protocol):
    """
    Abstract interface for cache providers supporting both sync and async.
    """
    async def get(self, key: str) -> Optional[Any]: ...
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool: ...
    async def delete(self, key: str) -> bool: ...
    async def invalidate_pattern(self, pattern: str) -> int: ...

    def get_sync(self, key: str) -> Optional[Any]: ...
    def set_sync(self, key: str, value: Any, ttl: int = 3600) -> bool: ...
    def invalidate_pattern_sync(self, pattern: str) -> int: ...

from .config import settings

class RedisCacheProvider:
    """
    Production-grade Redis cache implementation handling both Sync and Async contexts.
    Maintains separate connection pools for sync (redis-py) and async (redis.asyncio).
    """
    def __init__(self, host: str = settings.REDIS_HOST, port: int = settings.REDIS_PORT, db: int = settings.REDIS_DB_CACHE):
        self.redis_url = f"redis://{host}:{port}/{db}"
        self._aredis: Optional[aredis.Redis] = None  # Async client
        self._sredis: Optional[redis.Redis] = None   # Sync client
        self._enabled = True

    # --- Async Methods ---
    async def _get_aredis(self) -> Optional[aredis.Redis]:
        if not self._enabled: return None
        if self._aredis is None:
            try:
                self._aredis = aredis.from_url(self.redis_url, decode_responses=True, socket_timeout=2)
                await self._aredis.ping()
                logger.info(f"✅ Async Redis connected to {self.redis_url}")
            except Exception as e:
                logger.warning(f"⚠️ Async Redis unavailable: {e}")
                self._enabled = False
                return None
        return self._aredis

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_aredis()
        if not client: return None
        try:
            val = await client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        client = await self._get_aredis()
        if not client: return False
        try:
            await client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        client = await self._get_aredis()
        if not client: return False
        try:
            await client.delete(key)
            return True
        except Exception as e:
             logger.error(f"Cache DELETE error: {e}")
             return False

    async def invalidate_pattern(self, pattern: str) -> int:
        client = await self._get_aredis()
        if not client: return 0
        try:
            count = 0
            async for key in client.scan_iter(match=pattern):
                await client.delete(key)
                count += 1
            if count > 0: logger.info(f"Async Invalidated {count} keys matching '{pattern}'")
            return count
        except Exception as e:
            logger.error(f"Cache INVALIDATE error: {e}")
            return 0

    # --- Sync Methods ---
    def _get_sredis(self) -> Optional[redis.Redis]:
        if not self._enabled: return None
        if self._sredis is None:
            try:
                self._sredis = redis.from_url(self.redis_url, decode_responses=True, socket_timeout=2)
                self._sredis.ping()
                logger.info(f"✅ Sync Redis connected to {self.redis_url}")
            except Exception as e:
                logger.warning(f"⚠️ Sync Redis unavailable: {e}")
                self._enabled = False
                return None
        return self._sredis

    def get_sync(self, key: str) -> Optional[Any]:
        client = self._get_sredis()
        if not client: return None
        try:
            val = client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.error(f"Sync Cache GET error: {e}")
            return None

    def set_sync(self, key: str, value: Any, ttl: int = 3600) -> bool:
        client = self._get_sredis()
        if not client: return False
        try:
            client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Sync Cache SET error: {e}")
            return False

    def invalidate_pattern_sync(self, pattern: str) -> int:
        client = self._get_sredis()
        if not client: return 0
        try:
             # Scan is safe for production
            count = 0
            for key in client.scan_iter(match=pattern):
                client.delete(key)
                count += 1
            if count > 0: logger.info(f"Sync Invalidated {count} keys matching '{pattern}'")
            return count
        except Exception as e:
            logger.error(f"Sync Cache INVALIDATE error: {e}")
            return 0

global_cache = RedisCacheProvider()

def cached(ttl: int = 3600, key_builder: Optional[Callable[..., str]] = None):
    """
    Universal decorator for caching both sync and async function results.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        is_async = inspect.iscoroutinefunction(func)

        def _build_key(args, kwargs):
            if key_builder:
                return key_builder(*args, **kwargs)
            # Default key generation
            # args[0] is often 'self', which we might want to skip if it's an object instance
            # For robustness, we hash using the function's qualname and arguments

            # Simple approach: repr of args.
            # Note: Tying cache to 'self' (instance) is often wrong for services unless 'self' is stateless or part of identity.
            # Assuming stateless services for now or that repr(self) is consistent.

            # Improvement: If method, maybe skip self?
            # We'll use the full args for safety, relying on robust repr.
            key_content = f"{func.__module__}:{func.__qualname__}:{args}:{kwargs}"
            key_hash = hashlib.md5(key_content.encode()).hexdigest()
            return f"cache:{key_hash}"

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = _build_key(args, kwargs)
                cached_val = await global_cache.get(cache_key)
                if cached_val is not None:
                    logger.debug(f"💎 Async Cache HIT: {cache_key}")
                    return cached_val

                result = await func(*args, **kwargs)

                if result is not None:
                    await global_cache.set(cache_key, result, ttl=ttl)
                return result
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                cache_key = _build_key(args, kwargs)
                cached_val = global_cache.get_sync(cache_key)
                if cached_val is not None:
                    logger.debug(f"💎 Sync Cache HIT: {cache_key}")
                    return cached_val

                result = func(*args, **kwargs)

                if result is not None:
                    global_cache.set_sync(cache_key, result, ttl=ttl)
                return result
            return sync_wrapper

    return decorator
