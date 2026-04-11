import os
import logging
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from utils.request_id import set_request_id, init_request_id_logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from utils.telemetry import init_telemetry, instrument_fastapi
from config import config

logging.basicConfig(level=logging.INFO)


def _api_key_or_ip(request):
    """Key rate limiter on API key if present, fall back to IP."""
    return request.headers.get("X-API-Key") or get_remote_address(request)


limiter = Limiter(key_func=_api_key_or_ip, default_limits=["120/minute"])
init_request_id_logging()
init_telemetry()


def _validate_startup():
    if not os.getenv("JWT_SECRET_KEY"):
        raise RuntimeError("JWT_SECRET_KEY is not set — refusing to start.")
    if not os.getenv("ASTRA_API_KEY"):
        logging.warning("STARTUP WARNING: ASTRA_API_KEY not set")
    if not os.getenv("OLLAMA_HOST") and not os.getenv("DEFAULT_MODEL"):
        logging.warning("STARTUP WARNING: OLLAMA_HOST not set")


_validate_startup()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logging.info("🚀 ASTRA starting up")

    try:
        from api.ws_stream import broadcast as _ws_broadcast
    except Exception as e:
        logging.warning("WebSocket broadcast unavailable: %s", e)

        def _ws_broadcast(msg):
            return None

    # Eager Brain init — eliminates 8-15s first-request latency (P-1)
    try:
        from core.brain_singleton import get_brain
        import asyncio as _asyncio

        loop = _asyncio.get_event_loop()
        await loop.run_in_executor(None, get_brain)
        logging.info("🧠 Brain pre-initialized")
    except Exception as e:
        logging.warning("Brain pre-init failed: %s", e)

    from core.background import start_all

    _tasks = await start_all(_ws_broadcast)

    yield  # ── App is running ─────────────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logging.info("🛑 ASTRA shutting down")
    from core.background import stop_all

    await stop_all(_tasks)
    try:
        from core.brain_singleton import teardown_brain

        teardown_brain(None)
    except Exception as e:
        logging.warning("Brain teardown: %s", e)
    try:
        from core.observability import get_store

        get_store().flush()
    except Exception:
        pass


app = FastAPI(title="ASTRA", version="5.1", lifespan=lifespan)
instrument_fastapi(app)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or set_request_id()
        set_request_id(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

from api.routers.auth import router as auth_router
from api.routers.users import router as users_router
from api.routers.threads import router as threads_router
from api.routers.dashboard import router as dashboard_router
from auth.usage_middleware import UsageMiddleware
from api.routers import (
    chat,
    chat_stream,
    memory,
    model,
    health,
    feedback,
    observability,
    execute,
)

app.add_middleware(UsageMiddleware)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(threads_router)
app.include_router(chat.router)
app.include_router(chat_stream.router)
app.include_router(memory.router)
app.include_router(model.router)
app.include_router(health.router)
app.include_router(feedback.router)
app.include_router(observability.router)
app.include_router(execute.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.host, port=config.port, reload=config.debug)
