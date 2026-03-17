# core/observability.py — Per-request step timing
import time
import logging
from typing import Dict, List, Optional
from collections import deque
import threading

logger = logging.getLogger(__name__)

class RequestTrace:
    def __init__(self, request_id: str, user_input: str):
        self.request_id = request_id
        self.user_input = user_input[:80]
        self.steps: List[Dict] = []
        self.start_time = time.time()
        self._step_start: Optional[float] = None
        self._current_step: Optional[str] = None

    def step_start(self, name: str):
        self._current_step = name
        self._step_start   = time.time()

    def step_end(self, name: str = None, meta: str = ""):
        name = name or self._current_step or "unknown"
        duration_ms = round((time.time() - (self._step_start or self.start_time)) * 1000)
        self.steps.append({
            "step":     name,
            "ms":       duration_ms,
            "meta":     meta,
        })
        logger.info("⏱  [%s] %s: %dms%s",
                    self.request_id[:8],
                    name,
                    duration_ms,
                    f" ({meta})" if meta else "")
        self._step_start   = None
        self._current_step = None

    def finish(self, intent: str = "", agent: str = "") -> Dict:
        total_ms = round((time.time() - self.start_time) * 1000)
        result = {
            "request_id": self.request_id,
            "total_ms":   total_ms,
            "intent":     intent,
            "agent":      agent,
            "steps":      self.steps,
        }
        logger.info("✅ [%s] total: %dms | intent=%s agent=%s",
                    self.request_id[:8], total_ms, intent, agent)
        return result

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "input":      self.user_input,
            "steps":      self.steps,
            "elapsed_ms": round((time.time() - self.start_time) * 1000),
        }


class ObservabilityStore:
    def __init__(self, maxlen: int = 50):
        self._traces: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, trace: Dict):
        with self._lock:
            self._traces.append(trace)

    def get_recent(self, n: int = 10) -> List[Dict]:
        with self._lock:
            return list(self._traces)[-n:]

    def get_stats(self) -> Dict:
        with self._lock:
            traces = list(self._traces)
        if not traces:
            return {}
        totals = [t["total_ms"] for t in traces]
        step_times: Dict[str, List[int]] = {}
        for t in traces:
            for s in t.get("steps", []):
                step_times.setdefault(s["step"], []).append(s["ms"])
        return {
            "requests":     len(traces),
            "avg_total_ms": round(sum(totals) / len(totals)),
            "p95_ms":       sorted(totals)[int(len(totals) * 0.95)] if totals else 0,
            "per_step_avg": {
                k: round(sum(v) / len(v))
                for k, v in step_times.items()
            },
        }


_store = ObservabilityStore()

def get_store() -> ObservabilityStore:
    return _store
