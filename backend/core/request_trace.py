# core/request_trace.py
# Request tracing — one UUID per query, logged at every pipeline step
# grep any request_id across all logs to trace a slow/broken query
import uuid
import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_local = threading.local()


def new_trace(user_input: str = "") -> str:
    """Start a new trace. Returns request_id."""
    rid = str(uuid.uuid4())[:8]   # short 8-char ID
    _local.request_id   = rid
    _local.start_time   = time.time()
    _local.user_input   = user_input[:60]
    _local.steps        = []
    logger.info("▶ [%s] START: %s", rid, user_input[:60])
    return rid


def get_id() -> Optional[str]:
    return getattr(_local, "request_id", None)


def step(name: str, detail: str = ""):
    """Log a pipeline step."""
    rid = get_id()
    if not rid:
        return
    elapsed = round((time.time() - _local.start_time) * 1000)
    msg     = f"  [{rid}] +{elapsed}ms {name}"
    if detail:
        msg += f" — {detail[:80]}"
    logger.info(msg)
    _local.steps.append({"step": name, "ms": elapsed, "detail": detail[:80]})


def finish(intent: str = "", agent: str = "") -> dict:
    """End trace, return timing summary."""
    rid = get_id()
    if not rid:
        return {}
    total = round((time.time() - _local.start_time) * 1000)
    logger.info("◀ [%s] DONE %dms intent=%s agent=%s",
                rid, total, intent, agent)
    summary = {
        "request_id": rid,
        "total_ms":   total,
        "intent":     intent,
        "agent":      agent,
        "steps":      list(getattr(_local, "steps", [])),
    }
    _local.request_id = None
    return summary
