import logging
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Load whisper model once (tiny = fast on M4)
_model = None

def get_model():
    global _model
    if _model is None:
        logger.info("🧠 Loading Whisper model (tiny)...")
        _model = WhisperModel("tiny", device="cpu", compute_type="int8")
        logger.info("✅ Whisper ready")
    return _model


def record_audio(duration: int = 5, sample_rate: int = 16000) -> np.ndarray:
    """Record audio from microphone."""
    logger.info(f"🎤 Recording for {duration}s...")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    return audio.flatten()


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe audio array to text using faster-whisper."""
    model = get_model()
    segments, _ = model.transcribe(audio, beam_size=5, language="en")
    text = " ".join(seg.text.strip() for seg in segments).strip()
    logger.info(f"📝 Transcribed: {text}")
    return text


def listen(duration: int = 5) -> str:
    """Record and transcribe in one call."""
    audio = record_audio(duration=duration)
    return transcribe(audio)


def is_silent(audio: np.ndarray, threshold: float = 0.01) -> bool:
    """Check if audio is just silence."""
    return float(np.max(np.abs(audio))) < threshold
