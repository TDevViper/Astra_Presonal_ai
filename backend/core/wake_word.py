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


_listener_thread = None
_stop_event = None

def start_wake_word_listener(callback=None):
    global _listener_thread, _stop_event
    if not PORCUPINE_AVAILABLE:
        logger.info("Wake word listener skipped — not available in this environment")
        return None
    try:
        import pvporcupine
        import sounddevice as sd
        import numpy as np
        import threading

        api_key = os.getenv("PICOVOICE_API_KEY", "")
        if not api_key:
            logger.warning("PICOVOICE_API_KEY not set — wake word disabled")
            return None

        porcupine = pvporcupine.create(access_key=api_key, keywords=["hey siri"])
        _stop_event = threading.Event()

        def _listen():
            with sd.InputStream(samplerate=porcupine.sample_rate,
                                 channels=1, dtype="int16",
                                 blocksize=porcupine.frame_length) as stream:
                logger.info("Wake word listener started")
                while not _stop_event.is_set():
                    audio, _ = stream.read(porcupine.frame_length)
                    result = porcupine.process(audio.flatten())
                    if result >= 0:
                        logger.info("Wake word detected!")
                        if callback:
                            callback()
            porcupine.delete()

        _listener_thread = threading.Thread(target=_listen, daemon=True)
        _listener_thread.start()
        return _listener_thread
    except Exception as e:
        logger.warning(f"Wake word listener failed to start: {e}")
        return None


def stop_wake_word_listener():
    global _stop_event
    if _stop_event:
        _stop_event.set()
        logger.info("Wake word listener stopped")
