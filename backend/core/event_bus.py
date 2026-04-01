# core/event_bus.py — Lightweight async event bus for ASTRA
import threading
import time
import logging
from typing import Callable, Dict, List, Any
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: deque = deque(maxlen=100)
        self._lock = threading.Lock()

    def subscribe(self, event: str, handler: Callable):
        with self._lock:
            self._subscribers[event].append(handler)

    def publish(self, event: str, data: Any = None):
        payload = {
            "event": event,
            "data": data,
            "ts": time.time(),
        }
        self._history.append(payload)
        logger.debug("📡 event: %s | %s", event, str(data)[:80])

        with self._lock:
            handlers = list(self._subscribers.get(event, []))

        for handler in handlers:
            try:
                threading.Thread(target=handler, args=(payload,), daemon=True).start()
            except Exception as e:
                logger.warning("event handler error [%s]: %s", event, e)

    def get_history(self, limit: int = 20) -> list:
        return list(self._history)[-limit:]

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "subscriptions": {k: len(v) for k, v in self._subscribers.items()},
                "history_count": len(self._history),
            }


# Global singleton
_bus = EventBus()


def publish(event: str, data: Any = None):
    _bus.publish(event, data)


def subscribe(event: str, handler: Callable):
    _bus.subscribe(event, handler)


def get_history(limit: int = 20) -> list:
    return _bus.get_history(limit)


def get_stats() -> dict:
    return _bus.get_stats()


# Standard events
EVENTS = {
    "request_start": "request_start",
    "cache_hit": "cache_hit",
    "tool_called": "tool_called",
    "tool_done": "tool_done",
    "memory_recalled": "memory_recalled",
    "memory_updated": "memory_updated",
    "llm_start": "llm_start",
    "llm_done": "llm_done",
    "web_search_start": "web_search_start",
    "web_search_done": "web_search_done",
    "response_done": "response_done",
    "error": "error",
}
