# core/brain_singleton.py
import logging
import threading

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
    return _brain_instance


def teardown_brain(exception=None):
    global _brain_instance
    if _brain_instance is None:
        return
    logger.info("Brain teardown complete")


def safe_append_history(brain, role: str, content: str) -> None:
    """Thread-safe history append."""
    with _history_lock:
        brain.conversation_history.append({"role": role, "content": content})
