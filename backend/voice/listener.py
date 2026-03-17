import logging
import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

# Load whisper model once (tiny = fast on M4)
_model = None

# region agent log
def _dbg(hypothesis_id: str, message: str, data: dict):
    try:
        import time, json, urllib.request
        payload = {
            "sessionId": "4c1d8e",
            "runId": "whisper-403-debug",
            "hypothesisId": hypothesis_id,
            "location": "backend/voice/listener.py",
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        req = urllib.request.Request(
            "http://127.0.0.1:7482/ingest/9b816707-b54b-4d01-ae5f-e94ebab7cde8",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Debug-Session-Id": "4c1d8e"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1.5).read()
    except Exception:
        pass
# endregion agent log

def get_model():
    global _model
    if _model is None:
        logger.info("🧠 Loading Whisper model (tiny)...")
        # region agent log
        _dbg("H3-whisper-init", "Initializing WhisperModel", {"model": "small", "device": "cpu", "compute_type": "int8"})
        # endregion agent log
        try:
            # Import lazily so we can capture import-time failures (often model download / proxy issues).
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except Exception as e:
                # region agent log
                _dbg("H5-whisper-import", "faster_whisper import failed", {"errorType": type(e).__name__, "error": str(e)[:200]})
                # endregion agent log
                raise
            _model = WhisperModel("small", device="cpu", compute_type="int8")
        except Exception as e:
            # region agent log
            _dbg("H3-whisper-init", "WhisperModel init failed", {"errorType": type(e).__name__, "error": str(e)[:200]})
            # endregion agent log
            raise
        logger.info("✅ Whisper ready")
    return _model


def whisper_status() -> tuple[bool, str]:
    """
    Lightweight readiness check for /realtime/status.
    Must NOT trigger network downloads (common in locked-down networks).
    """
    try:
        # Reuse already-loaded model.
        if _model is not None:
            return True, "ready"

        from faster_whisper import WhisperModel  # type: ignore
        import os

        # Keep models in-repo so users can prefetch/cache them.
        download_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "whisper"))
        # Status check should never download; it should only detect whether files exist.
        WhisperModel("small", device="cpu", compute_type="int8", download_root=download_root, local_files_only=True)
        return True, "ready"
    except Exception as e:
        msg = str(e)
        if "403" in msg or "Forbidden" in msg:
            msg = "model download blocked (403). Pre-download models or run with network access."
        return False, msg

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
