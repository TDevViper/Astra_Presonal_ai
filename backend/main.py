import os, logging, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from utils.request_id import set_request_id, init_request_id_logging
from config import config

logging.basicConfig(level=logging.INFO)
init_request_id_logging()

def _validate_startup():
    if not os.getenv("ASTRA_API_KEY"):
        logging.warning("STARTUP WARNING: ASTRA_API_KEY not set")
    if not os.getenv("OLLAMA_HOST") and not os.getenv("DEFAULT_MODEL"):
        logging.warning("STARTUP WARNING: OLLAMA_HOST not set")

_validate_startup()

app = FastAPI(title="ASTRA", version="5.1")

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

from api.routers import chat, chat_stream, memory, model, health
app.include_router(chat.router)
app.include_router(chat_stream.router)
app.include_router(memory.router)
app.include_router(model.router)
app.include_router(health.router)

try:
    from api.ws_stream import broadcast as _ws_broadcast
    from core.proactive import set_broadcast
    set_broadcast(_ws_broadcast)
except Exception as e:
    logging.warning(f"Broadcast setup failed: {e}")

try:
    from core.smart_guardian import start as _start_guardian
    _start_guardian(broadcast_fn=_ws_broadcast)
except Exception as e:
    logging.warning(f"SmartGuardian failed: {e}")

try:
    from tools.plugin_watcher import start as _start_plugins
    _start_plugins()
except Exception as e:
    logging.warning(f"Plugin watcher failed: {e}")

try:
    from core.gpu_health import start as _start_gpu_health
    _start_gpu_health()
except Exception as e:
    logging.warning(f"GPU health failed: {e}")

try:
    from rag.watcher import start_watcher
    start_watcher(interval=30)
except Exception as e:
    logging.warning(f"Doc watcher failed: {e}")

from core.brain_singleton import teardown_brain

@app.on_event("shutdown")
async def _shutdown():
    teardown_brain(None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.host, port=config.port, reload=config.debug)
