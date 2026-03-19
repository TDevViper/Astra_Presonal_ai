import hashlib, json, logging, time, os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cache replies for 10 minutes; skip only very long responses (200+ words)
_CACHE_TTL       = int(os.getenv("CACHE_TTL_SECONDS", 600))   # 10 min default
_MAX_REPLY_WORDS = int(os.getenv("CACHE_MAX_WORDS",   200))   # was 40 — too tight

# Never cache these intents (time-sensitive or personal)
_SKIP_INTENTS = {"web_search", "memory_storage", "memory_recall", "error", "briefing"}


def _key(text: str, session_id: str = "default") -> str:
    """Cache key scoped to session — prevents cross-user response leakage."""
    scoped = f"{session_id}:{text.strip().lower()}"
    return "astra:reply:" + hashlib.sha256(scoped.encode()).hexdigest()[:32]


class ResponseCache:
    def __init__(self, ttl: int = _CACHE_TTL):
        self.ttl    = ttl
        self._redis = self._connect()
        self._local: Dict = {}
        self._hits  = 0
        self._misses = 0

    def _connect(self):
        try:
            import redis
            c = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                socket_connect_timeout=1,
                decode_responses=True,      # always get str back, not bytes
            )
            c.ping()
            logger.info("ResponseCache: Redis connected ✓")
            return c
        except Exception as e:
            logger.warning("Redis unavailable — using local dict cache: %s", e)
            return None

    def get(self, text: str, session_id: str = "default") -> Optional[Dict]:
        k = _key(text, session_id)
        try:
            if self._redis:
                raw = self._redis.get(k)
                if raw:
                    self._hits += 1
                    logger.debug("Cache HIT  (redis) hits=%d", self._hits)
                    return json.loads(raw)
            else:
                entry = self._local.get(k)
                if entry and (time.time() - entry["ts"]) < self.ttl:
                    self._hits += 1
                    logger.debug("Cache HIT  (local) hits=%d", self._hits)
                    return entry["result"]
        except Exception as e:
            logger.warning("ResponseCache.get error: %s", e)
        self._misses += 1
        return None

    def set(self, text: str, result: Dict, session_id: str = "default") -> None:
        # Skip uncacheable responses
        if result.get("intent") in _SKIP_INTENTS:
            return
        if len(result.get("reply", "").split()) > _MAX_REPLY_WORDS:
            return
        k = _key(text, session_id)
        try:
            if self._redis:
                self._redis.setex(k, self.ttl, json.dumps(result))
            else:
                self._local[k] = {"result": result, "ts": time.time()}
            logger.debug("Cache SET  key=%s ttl=%ds", k[-8:], self.ttl)
        except Exception as e:
            logger.warning("ResponseCache.set error: %s", e)

    def invalidate(self, text: str, session_id: str = "default") -> None:
        """Remove a specific entry (e.g. after memory update)."""
        k = _key(text, session_id)
        try:
            if self._redis:
                self._redis.delete(k)
            else:
                self._local.pop(k, None)
        except Exception as e:
            logger.warning("ResponseCache.invalidate error: %s", e)

    def flush(self) -> int:
        """Clear all ASTRA cache keys. Returns count deleted."""
        count = 0
        try:
            if self._redis:
                keys = self._redis.keys("astra:reply:*")
                if keys:
                    count = self._redis.delete(*keys)
            else:
                count = len(self._local)
                self._local.clear()
        except Exception as e:
            logger.warning("ResponseCache.flush error: %s", e)
        return count

    def stats(self) -> Dict:
        total = self._hits + self._misses
        return {
            "hits":       self._hits,
            "misses":     self._misses,
            "hit_rate":   round(self._hits / total, 3) if total else 0.0,
            "backend":    "redis" if self._redis else "local",
            "ttl_seconds": self.ttl,
        }
