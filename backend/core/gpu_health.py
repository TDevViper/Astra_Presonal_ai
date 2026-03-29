# core/gpu_health.py
# Background health-check for remote GPU Ollama server.
# Replaces per-request requests.get() calls in agent_loop and planner.
import threading
import time
import os
import logging

logger = logging.getLogger(__name__)

_GPU_HOST    = os.getenv("REMOTE_GPU_HOST", "")
_CHECK_EVERY = 15   # seconds
_TIMEOUT     = 1.5

_status = {"alive": False, "last_check": 0.0}
_lock   = threading.Lock()


def _check_once() -> bool:
    if not _GPU_HOST:
        return False
    try:
        import requests
        r = requests.get(_GPU_HOST, timeout=_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def _background_loop():
    while True:
        alive = _check_once()
        with _lock:
            _status["alive"]      = alive
            _status["last_check"] = time.time()
        logger.debug("GPU health: %s", "UP" if alive else "DOWN")
        time.sleep(_CHECK_EVERY)


def start():
    """Call once at app startup to begin background health checks."""
    if not _GPU_HOST:
        logger.info("REMOTE_GPU_HOST not set — GPU health-check disabled")
        return
    t = threading.Thread(target=_background_loop, daemon=True, name="gpu-health")
    t.start()
    logger.info("GPU health-check started (every %ds)", _CHECK_EVERY)


def gpu_alive() -> bool:
    """Fast cached check — no network call."""
    with _lock:
        return bool(_GPU_HOST) and _status["alive"]
