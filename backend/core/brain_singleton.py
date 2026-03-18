# core/brain_singleton.py
import logging
import threading
from flask import g

logger = logging.getLogger(__name__)

_brain_instance = None
_brain_lock     = threading.Lock()
_history_lock   = threading.Lock()


def get_brain():
    global _brain_instance
    if _brain_instance is None:
        with _brain_lock:
            if _brain_instance is None:
                from core.brain import Brain
                logger.info("Initializing Brain instance...")
                _brain_instance = Brain()

    try:
        if not hasattr(g, '_brain_history_snapshot'):
            with _history_lock:
                g._brain_history_snapshot = list(_brain_instance.conversation_history)
    except RuntimeError:
        pass

    return _brain_instance


def teardown_brain(exception=None):
    global _brain_instance
    if _brain_instance is None:
        return
    try:
        if hasattr(g, '_brain_history_snapshot'):
            with _history_lock:
                snapshot = g._brain_history_snapshot
                current  = _brain_instance.conversation_history
                # Keep only turns added during this request + trim to 12
                new_turns = current[len(snapshot):]
                _brain_instance.conversation_history = (snapshot + new_turns)[-12:]
    except RuntimeError:
        pass


def safe_append_history(brain, role: str, content: str) -> None:
    """Thread-safe history append — call instead of direct list.append."""
    with _history_lock:
        brain.conversation_history.append({"role": role, "content": content})
