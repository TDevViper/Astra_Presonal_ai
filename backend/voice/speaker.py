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
    """Only return voices that have .pt files on disk."""
    import os
    voices_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voices")
    available = {f.replace(".pt", "") for f in os.listdir(voices_dir) if f.endswith(".pt")}
    all_voices = [
        {"id": "am_michael", "name": "Michael (US Male)"},
        {"id": "am_adam",    "name": "Adam (US Male)"},
        {"id": "bm_george",  "name": "George (UK Male)"},
        {"id": "af_sarah",   "name": "Sarah (US Female)"},
        {"id": "bf_emma",    "name": "Emma (UK Female)"},
        {"id": "af_bella",   "name": "Bella (US Female)"},
    ]
    return [v for v in all_voices if v["id"] in available]
