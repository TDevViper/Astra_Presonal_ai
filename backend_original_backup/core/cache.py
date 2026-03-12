"""
Unified response cache.
Uses Redis if available, falls back to in-process dict.
This fixes the multi-worker cache miss bug.
"""
import hashlib
import time
import logging
import json

logger = logging.getLogger(__name__)

_local_cache: dict = {}
_CACHE_TTL = 60
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        import os
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(url, socket_connect_timeout=1)
        r.ping()
        _redis_client = r
        logger.info("Cache: Redis connected")
    except Exception as e:
        logger.info(f"Cache: Redis unavailable ({e}), using local dict")
        _redis_client = None
    return _redis_client


def cache_key(text: str) -> str:
    return "astra:resp:" + hashlib.md5(text.strip().lower().encode()).hexdigest()


def get_cached(text: str):
    key = cache_key(text)
    r = _get_redis()
    if r:
        try:
            val = r.get(key)
            if val:
                logger.debug("Cache hit (Redis)")
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
    # fallback to local
    entry = _local_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        logger.debug("Cache hit (local)")
        return entry["result"]
    return None


def set_cached(text: str, result: dict):
    if len(result.get("reply", "").split()) >= 40:
        return  # don't cache long responses
    key = cache_key(text)
    r = _get_redis()
    if r:
        try:
            r.setex(key, _CACHE_TTL, json.dumps(result))
            return
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
    _local_cache[key] = {"result": result, "ts": time.time()}


def clear_cache():
    global _local_cache
    _local_cache = {}
    r = _get_redis()
    if r:
        try:
            keys = r.keys("astra:resp:*")
            if keys:
                r.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}")
