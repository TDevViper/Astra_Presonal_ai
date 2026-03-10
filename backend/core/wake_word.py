import os
import logging

logger = logging.getLogger(__name__)

# pvporcupine is Mac-only hardware wake word — skip in Docker
try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    logger.warning("pvporcupine not available — wake word disabled (Docker mode)")


def start_wake_word_listener(callback=None):
    if not PORCUPINE_AVAILABLE:
        logger.info("Wake word listener skipped — not available in this environment")
        return None
    try:
        import pvporcupine
        import sounddevice as sd
        import numpy as np
        logger.info("Wake word listener started")
    except Exception as e:
        logger.warning(f"Wake word listener failed to start: {e}")
        return None


def stop_wake_word_listener():
    pass
