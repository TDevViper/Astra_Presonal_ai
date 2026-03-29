"""
FastAPI middleware — automatically logs every authenticated request.
Attaches to the app in main.py.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from auth.usage_tracker import init_db, log_event

logger = logging.getLogger(__name__)
init_db()

SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


class UsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Only log authenticated requests
        try:
            user = getattr(request.state, "current_user", None)
            if user:
                log_event(
                    user_id     = user.get("id", "unknown"),
                    username    = user.get("username", "unknown"),
                    role        = user.get("role", "unknown"),
                    endpoint    = request.url.path,
                    method      = request.method,
                    status_code = response.status_code,
                    duration_ms = round(duration_ms, 2),
                )
        except Exception as e:
            logger.debug("Usage log error: %s", e)

        return response
