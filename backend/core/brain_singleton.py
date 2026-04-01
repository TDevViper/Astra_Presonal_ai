# core/brain_singleton.py
import logging
import threading

logger = logging.getLogger(__name__)
_brain_lock = threading.Lock()
_brain_instance = None


def get_brain():
    """Returns the shared Brain instance (stateless — no conversation_history on it)."""
    global _brain_instance
    if _brain_instance is None:
        with _brain_lock:
            if _brain_instance is None:
                from core.brain import Brain

                logger.info("Initializing Brain instance...")
                _brain_instance = Brain()
    return _brain_instance


def load_request_history(n: int = 15) -> list:
    """Load a fresh per-request history snapshot from DB. Never shared."""
    try:
        from memory_db import load_recent_history

        return load_recent_history(n=n)
    except Exception as e:
        logger.warning("load_request_history failed: %s", e)
        return []


def teardown_brain(exception=None):
    global _brain_instance
    if _brain_instance is None:
        return
    logger.info("Brain teardown complete")
