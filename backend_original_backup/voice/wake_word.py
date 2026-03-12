import logging

logger = logging.getLogger(__name__)

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    logger.warning("pvporcupine not available — wake word disabled (Docker mode)")


def start_wake_word_listener(callback=None):
    if not PORCUPINE_AVAILABLE:
        return None
    try:
        logger.info("Wake word listener started")
    except Exception as e:
        logger.warning(f"Wake word failed: {e}")
        return None


def stop_wake_word_listener():
    pass
