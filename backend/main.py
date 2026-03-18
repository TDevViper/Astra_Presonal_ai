import os, logging, sys
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
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
init_request_id_logging()
init_telemetry()

def _validate_startup():
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
        _ws_broadcast = lambda msg: None

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
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000","http://localhost:3001",
                   "http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:3001"],
    allow_methods=["*"], allow_headers=["*"],
)

from api.routers import chat, chat_stream, memory, model, health, feedback, observability
app.include_router(chat.router)
app.include_router(chat_stream.router)
app.include_router(memory.router)
app.include_router(model.router)
app.include_router(health.router)
app.include_router(feedback.router)
app.include_router(observability.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.host, port=config.port, reload=config.debug)
