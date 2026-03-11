# ==========================================
# core/response_cache.py
# ==========================================
import hashlib, json, logging, time, os
from typing import Dict, Optional

logger = logging.getLogger(__name__)
_CACHE_TTL      = 60
_MAX_REPLY_WORDS = 40

def _key(text: str) -> str:
    return "astra:reply:" + hashlib.md5(text.strip().lower().encode()).hexdigest()

class ResponseCache:
    def __init__(self, ttl: int = _CACHE_TTL):
        self.ttl    = ttl
        self._redis = self._connect()
        self._local: Dict = {}
        if self._redis:
            logger.info("✅ ResponseCache: Redis")
        else:
            logger.warning("⚠️  ResponseCache: falling back to in-process dict")

    def _connect(self):
        try:
            import redis
            c = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                socket_connect_timeout=1,
            )
            c.ping()
            return c
        except Exception as e:
            logger.warning("Redis unavailable: %s", e)
            return None

    def get(self, text: str) -> Optional[Dict]:
        k = _key(text)
        try:
            if self._redis:
                raw = self._redis.get(k)
                if raw:
                    logger.info("⚡ Cache hit (Redis)")
                    return json.loads(raw)
            else:
                entry = self._local.get(k)
                if entry and (time.time() - entry["ts"]) < self.ttl:
                    logger.info("⚡ Cache hit (local)")
                    return entry["result"]
        except Exception as e:
            logger.warning("ResponseCache.get error: %s", e)
        return None

    def set(self, text: str, result: Dict) -> None:
        if len(result.get("reply", "").split()) >= _MAX_REPLY_WORDS:
            return
        k = _key(text)
        try:
            if self._redis:
                self._redis.setex(k, self.ttl, json.dumps(result))
            else:
                self._local[k] = {"result": result, "ts": time.time()}
        except Exception as e:
            logger.warning("ResponseCache.set error: %s", e)
