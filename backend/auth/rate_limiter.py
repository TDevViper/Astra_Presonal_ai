"""
Per-user rate limiting using Redis (sliding window).
Falls back to in-memory if Redis is unavailable.
"""
import time
import logging
import os
from collections import defaultdict, deque
from typing import Dict
from fastapi import HTTPException, status, Depends
from auth.rbac import get_current_user

logger = logging.getLogger(__name__)

# ── Limits per role (requests per minute) ────────────────────────────────────
ROLE_LIMITS: Dict[str, int] = {
    "guest": 5,
    "user":  20,
    "admin": 60,
    "owner": 999,
}

# ── In-memory sliding window fallback ────────────────────────────────────────
_windows: Dict[str, deque] = defaultdict(deque)


def _check_redis(user_id: str, limit: int) -> bool:
    try:
        import redis
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                                 socket_connect_timeout=1)
        key = f"rl:{user_id}"
        pipe = r.pipeline()
        now  = time.time()
        pipe.zremrangebyscore(key, 0, now - 60)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 60)
        results = pipe.execute()
        count = results[2]
        return count <= limit
    except Exception:
        return None   # Redis unavailable — fall through


def _check_memory(user_id: str, limit: int) -> bool:
    now = time.time()
    dq  = _windows[user_id]
    while dq and dq[0] < now - 60:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True


def check_rate_limit(user_id: str, role: str):
    limit  = ROLE_LIMITS.get(role, 5)
    result = _check_redis(user_id, limit)
    if result is None:
        result = _check_memory(user_id, limit)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded — {limit} requests/minute for role '{role}'",
            headers={"Retry-After": "60"},
        )


def rate_limit(current_user=Depends(get_current_user)):
    """FastAPI dependency — attach to any endpoint to enforce per-user limits."""
    check_rate_limit(current_user["id"], current_user["role"])
    return current_user
