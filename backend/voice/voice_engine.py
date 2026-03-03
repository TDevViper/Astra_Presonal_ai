# ==========================================
# voice/voice_engine.py — JARVIS Edition
# Smooth STT + confident TTS
# ==========================================

import logging
import threading
import queue
import tempfile
import os
import numpy as np

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────
SAMPLE_RATE    = 16000
CHANNELS       = 1
RECORD_SECONDS = 5
WAKE_WORD      = "hey astra"


# ── STT — Speech to Text ──────────────────

def transcribe_audio(audio_data: np.ndarray) -> str:
    """Convert audio to text using faster-whisper."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")

        # Save to temp file
        import scipy.io.wavfile as wav
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            wav.write(tmp_path, SAMPLE_RATE, audio_data)

        segments, _ = model.transcribe(tmp_path, beam_size=5, language="en")
        text = " ".join(s.text for s in segments).strip()

        os.unlink(tmp_path)
        logger.info(f"🎤 Transcribed: {text}")
        return text

    except Exception as e:
        logger.error(f"❌ Transcription error: {e}")
        return ""


def record_audio(duration: int = RECORD_SECONDS) -> np.ndarray:
    """Record audio from microphone."""
    import sounddevice as sd
    logger.info(f"🎤 Recording {duration}s...")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16"
    )
    sd.wait()
    return audio.flatten()


def listen_once(duration: int = 5) -> str:
    """Record + transcribe in one call."""
    audio = record_audio(duration)
    return transcribe_audio(audio)


# ── TTS — Text to Speech ──────────────────

_tts_lock = threading.Lock()


def speak(text: str, rate: int = 185, volume: float = 1.0) -> None:
    """
    Speak text in JARVIS-style confident tone.
    rate=185 — slightly faster than default, crisp and clear.
    """
    if not text or not text.strip():
        return

    # Clean text for speech — remove markdown, emojis
    import re
    clean = re.sub(r'[*_`#]', '', text)
    clean = re.sub(r'https?://\S+', 'link', clean)
    clean = re.sub(r'[^\x00-\x7F]+', '', clean)  # Remove non-ASCII
    clean = re.sub(r'\s+', ' ', clean).strip()

    if not clean:
        return

    def _speak():
        with _tts_lock:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate',   rate)
                engine.setProperty('volume', volume)

                # Use best available voice — prefer deep/clear
                voices = engine.getProperty('voices')
                preferred = None
                for v in voices:
                    name = v.name.lower()
                    # macOS: prefer Alex or Daniel (clear male voices)
                    if any(n in name for n in ['alex', 'daniel', 'fred']):
                        preferred = v.id
                        break

                if preferred:
                    engine.setProperty('voice', preferred)

                logger.info(f"🔊 Speaking: {clean[:60]}...")
                engine.say(clean)
                engine.runAndWait()
                engine.stop()

            except Exception as e:
                logger.error(f"❌ TTS error: {e}")
                # Fallback to macOS say command
                try:
                    os.system(f'say -r {rate} "{clean[:200]}"')
                except Exception:
                    pass

    # Speak in background thread — don't block
    t = threading.Thread(target=_speak, daemon=True)
    t.start()


def speak_blocking(text: str, rate: int = 185) -> None:
    """Speak and wait until done."""
    if not text:
        return
    import re
    clean = re.sub(r'[*_`#\U00010000-\U0010ffff]', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    try:
        os.system(f'say -r {rate} "{clean[:300]}"')
    except Exception as e:
        logger.error(f"TTS blocking error: {e}")


# ── Wake Word Detection ────────────────────

class WakeWordListener:
    """
    Continuously listens for wake word.
    When detected, triggers callback with transcribed query.
    """

    def __init__(self, callback, wake_word: str = WAKE_WORD):
        self.callback  = callback
        self.wake_word = wake_word.lower()
        self._running  = False
        self._thread   = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"👂 Wake word listener started — say '{self.wake_word}'")

    def stop(self):
        self._running = False
        logger.info("🔇 Wake word listener stopped")

    def _loop(self):
        import sounddevice as sd
        while self._running:
            try:
                # Short listen for wake word
                audio = sd.rec(
                    int(2 * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16"
                )
                sd.wait()
                text = transcribe_audio(audio.flatten()).lower()

                if self.wake_word in text:
                    logger.info(f"🎯 Wake word detected!")
                    speak("Yes?", rate=200)

                    # Now listen for actual command
                    query = listen_once(duration=6)
                    if query:
                        logger.info(f"📝 Command: {query}")
                        self.callback(query)

            except Exception as e:
                logger.error(f"Wake word loop error: {e}")
