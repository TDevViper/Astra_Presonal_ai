# speaker.py — routes all TTS through Kokoro
import logging
import threading
from tts_kokoro import speak

logger = logging.getLogger(__name__)

def get_engine():
    return None  # no longer needed

def speak_async(text: str) -> None:
    t = threading.Thread(target=speak, args=(text,), daemon=True)
    t.start()

def list_voices():
    return [
        {"id": "am_michael", "name": "Michael (US Male)"},
        {"id": "am_adam",    "name": "Adam (US Male)"},
        {"id": "bm_george",  "name": "George (UK Male)"},
        {"id": "af_sarah",   "name": "Sarah (US Female)"},
        {"id": "bf_emma",    "name": "Emma (UK Female)"},
    ]
