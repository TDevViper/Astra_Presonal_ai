# ==========================================
# voice/voice_engine.py — JARVIS Edition
# Smooth STT + Kokoro TTS
# ==========================================

import logging
import threading
import tempfile
import os
import re
import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE    = 16000
CHANNELS       = 1
RECORD_SECONDS = 5
WAKE_WORD      = "hey astra"


# ── STT — Speech to Text ──────────────────

def transcribe_audio(audio_data: np.ndarray) -> str:
    try:
        from faster_whisper import WhisperModel
        import scipy.io.wavfile as wav
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            wav.write(tmp_path, SAMPLE_RATE, audio_data)
        segments, _ = model.transcribe(tmp_path, beam_size=5, language="en")
        text = " ".join(s.text for s in segments).strip()
        os.unlink(tmp_path)
        logger.info(f"Transcribed: {text}")
        return text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return ""


def record_audio(duration: int = RECORD_SECONDS) -> np.ndarray:
    import sounddevice as sd
    logger.info(f"Recording {duration}s...")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16"
    )
    sd.wait()
    return audio.flatten()


def listen_once(duration: int = 5) -> str:
    audio = record_audio(duration)
    return transcribe_audio(audio)


# ── TTS — Text to Speech (Kokoro) ─────────

_tts_lock = threading.Lock()


def _clean_text(text: str) -> str:
    clean = re.sub(r'[*_`#]', '', text)
    clean = re.sub(r'https?://\S+', 'link', clean)
    clean = re.sub(r'[^\x00-\x7F]+', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def speak(text: str, rate: int = 185, volume: float = 1.0) -> None:
    if not text or not text.strip():
        return
    clean = _clean_text(text)
    if not clean:
        return

    def _speak():
        with _tts_lock:
            try:
                from tts_kokoro import speak as kokoro_speak
                logger.info(f"Speaking: {clean[:60]}...")
                kokoro_speak(clean)
            except Exception as e:
                logger.error(f"TTS error: {e}")
                try:
                    os.system(f'say -r {rate} "{clean[:200]}"')
                except Exception:
                    pass

    t = threading.Thread(target=_speak, daemon=True)
    t.start()


def speak_blocking(text: str, rate: int = 185) -> None:
    if not text:
        return
    clean = _clean_text(text)
    try:
        from tts_kokoro import speak as kokoro_speak
        kokoro_speak(clean)
    except Exception as e:
        logger.error(f"TTS blocking error: {e}")
        os.system(f'say -r {rate} "{clean[:300]}"')


# ── Wake Word Detection ────────────────────

class WakeWordListener:
    def __init__(self, callback, wake_word: str = WAKE_WORD):
        self.callback  = callback
        self.wake_word = wake_word.lower()
        self._running  = False
        self._thread   = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"Wake word listener started — say '{self.wake_word}'")

    def stop(self):
        self._running = False
        logger.info("Wake word listener stopped")

    def _loop(self):
        import sounddevice as sd
        while self._running:
            try:
                audio = sd.rec(
                    int(2 * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16"
                )
                sd.wait()
                text = transcribe_audio(audio.flatten()).lower()
                if self.wake_word in text:
                    logger.info("Wake word detected!")
                    speak("Yes?")
                    query = listen_once(duration=6)
                    if query:
                        logger.info(f"Command: {query}")
                        self.callback(query)
            except Exception as e:
                logger.error(f"Wake word loop error: {e}")
