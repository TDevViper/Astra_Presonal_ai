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
        _model = WhisperModel("small", device="cpu", compute_type="int8")
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
    """Record and transcribe in one call with VAD trimming."""
    audio = record_audio(duration=duration)
    if not is_silent(audio):
        audio = vad_trim(audio)
    return transcribe(audio)


def is_silent(audio: np.ndarray, threshold: float = 0.008) -> bool:
    """Check silence using RMS energy."""
    return float(np.sqrt(np.mean(audio ** 2))) < threshold

def vad_trim(audio: np.ndarray, sample_rate: int = 16000, threshold: float = 0.008) -> np.ndarray:
    """Trim leading and trailing silence."""
    frame_len = int(sample_rate * 0.02)
    frames = [audio[i:i+frame_len] for i in range(0, len(audio)-frame_len, frame_len)]
    speech = [i for i, f in enumerate(frames) if float(np.sqrt(np.mean(f**2))) >= threshold]
    if not speech:
        return audio
    start = max(0, speech[0] - 3) * frame_len
    end   = min(len(frames), speech[-1] + 3) * frame_len
    return audio[start:end]
