"""
core/wake_word.py — Local wake word + STT using faster-whisper.
Replaces PicoVoice (paid API key) with 100% local inference.
No API key needed.
"""
import os
import logging
import threading

logger = logging.getLogger(__name__)

WAKE_PHRASE = os.getenv("WAKE_PHRASE", "hey astra").lower()
_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
_SAMPLE_RATE = 16000
_SILENCE_THRESHOLD = 500
_RECORD_SECONDS = 5

_listener_thread = None
_stop_event = None

try:
    import sounddevice as _sd
    import numpy as _np
    _AUDIO_AVAILABLE = True
except ImportError:
    _AUDIO_AVAILABLE = False
    logger.warning("sounddevice not installed — wake word disabled")

try:
    from faster_whisper import WhisperModel as _WhisperModel
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed — STT disabled")


def _rms(audio_chunk) -> float:
    import numpy as np
    return float(np.sqrt(np.mean(audio_chunk.astype(float) ** 2)))


def _record_audio(seconds: int = _RECORD_SECONDS):
    import sounddevice as sd
    frames = sd.rec(int(seconds * _SAMPLE_RATE), samplerate=_SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    return frames.flatten()


def _transcribe(audio) -> str:
    if not _WHISPER_AVAILABLE:
        return ""
    try:
        import tempfile
        import wave
        import os
        model = _WhisperModel(_WHISPER_MODEL, device="cpu", compute_type="int8")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        segments, _ = model.transcribe(tmp_path, language="en")
        os.unlink(tmp_path)
        return " ".join(s.text for s in segments).strip().lower()
    except Exception as e:
        logger.warning("transcribe error: %s", e)
        return ""


def start_wake_word_listener(callback=None):
    global _listener_thread, _stop_event
    if not _AUDIO_AVAILABLE or not _WHISPER_AVAILABLE:
        logger.info("Wake word listener skipped — missing dependencies")
        return None

    _stop_event = threading.Event()

    def _listen():
        import sounddevice as sd
        logger.info("🎤 Wake word listener started — say '%s'", WAKE_PHRASE)
        chunk_size = int(_SAMPLE_RATE * 0.5)
        with sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="int16", blocksize=chunk_size) as stream:
            while not _stop_event.is_set():
                chunk, _ = stream.read(chunk_size)
                if _rms(chunk) < _SILENCE_THRESHOLD:
                    continue
                audio = _record_audio(_RECORD_SECONDS)
                text = _transcribe(audio)
                if WAKE_PHRASE in text:
                    logger.info("✅ Wake phrase detected: '%s'", text)
                    if callback:
                        callback()

    _listener_thread = threading.Thread(target=_listen, daemon=True, name="wake-word")
    _listener_thread.start()
    return _listener_thread


def stop_wake_word_listener():
    global _stop_event
    if _stop_event:
        _stop_event.set()
        logger.info("Wake word listener stopped")
