# core/brain_singleton.py
# App-context managed Brain instance.
# One Brain per app (not per request) but thread-safe conversation history.
import logging
from flask import g

logger = logging.getLogger(__name__)

_brain_instance = None


def get_brain():
    """
    Returns the Brain instance.
    Uses Flask's g object to give each request its own conversation context
    while sharing the expensive initialized components (models, cache, memory).
    """
    global _brain_instance

    if _brain_instance is None:
        from core.brain import Brain
        logger.info("Initializing Brain instance...")
        _brain_instance = Brain()

    # Each request gets a fresh conversation snapshot
    # so concurrent requests don't corrupt each other's history
    try:
        if not hasattr(g, '_brain_history_saved'):
            g._brain_history_saved = list(_brain_instance.conversation_history)
            g._brain_history_saved  # touch it so Flask tracks it
    except RuntimeError:
        # Outside request context (e.g. tests) — just return the instance
        pass

    return _brain_instance


def teardown_brain(exception=None):
    """Call this in app teardown to restore conversation history after request."""
    global _brain_instance
    if _brain_instance is None:
        return
    try:
        if hasattr(g, '_brain_history_saved'):
            # Merge: keep last 12 turns combining saved + new
            new_turns = _brain_instance.conversation_history[len(g._brain_history_saved):]
            _brain_instance.conversation_history = (g._brain_history_saved + new_turns)[-12:]
    except RuntimeError:
        pass
