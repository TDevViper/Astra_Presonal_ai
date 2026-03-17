import platform
import threading, os, sys
import warnings
warnings.filterwarnings("ignore")

_BASE   = os.path.dirname(os.path.abspath(__file__))
_MODEL  = os.path.join(_BASE, "kokoro-v0_19.onnx")
_VOICES = os.path.join(_BASE, "voices")

# region agent log
def _dbg(hypothesis_id: str, message: str, data: dict):
    try:
        import time, json, urllib.request
        payload = {
            "sessionId": "4c1d8e",
            "runId": "kokoro-403-debug",
            "hypothesisId": hypothesis_id,
            "location": "backend/tts_kokoro.py",
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

try:
    # Allow forcing offline fallback in locked-down networks.
    if os.getenv("KOKORO_OFFLINE", "").lower() in ("1", "true", "yes"):
        raise RuntimeError("Kokoro disabled via KOKORO_OFFLINE")

    from kokoro import KPipeline
    import sounddevice as sd
    import torch

    # region agent log
    _dbg("H4-kokoro-init", "Initializing Kokoro pipeline", {"repo_id": "hexgrad/Kokoro-82M", "modelPathExists": os.path.exists(_MODEL)})
    # endregion agent log
    try:
        _pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M', model=_MODEL)
    except Exception as e:
        # If network/proxy blocks HF fetch, retry offline/local init.
        # region agent log
        _dbg("H6-kokoro-offline", "Kokoro init failed with repo_id; retrying without repo_id", {"errorType": type(e).__name__, "error": str(e)[:200]})
        # endregion agent log
        _pipeline = KPipeline(lang_code='a', model=_MODEL)

    # Always use system default output device (follows macOS audio routing)
    import sounddevice as _sd
    _sd.default.device = (None, _sd.default.device[1])

    # Pre-load default voice into memory at startup
    _voice_cache = {}
    _default_voice_path = os.path.join(_VOICES, "af_bella.pt")
    if os.path.exists(_default_voice_path):
        _voice_cache["af_bella"] = torch.load(_default_voice_path, weights_only=True)

    KOKORO_AVAILABLE = True
    print("[KokoroTTS] ✅ Kokoro v1 ready")
except Exception as e:
    # region agent log
    _dbg("H4-kokoro-init", "Kokoro init failed (falling back)", {"errorType": type(e).__name__, "error": str(e)[:200]})
    # endregion agent log
    print(f"[KokoroTTS] Not available ({e}) — falling back to macOS say")
    KOKORO_AVAILABLE = False

def _load_voice(voice: str):
    if not KOKORO_AVAILABLE:
        return voice
    if voice in _voice_cache:
        return _voice_cache[voice]
    import torch
    path = os.path.join(_VOICES, f"{voice}.pt")
    if os.path.exists(path):
        v = torch.load(path, weights_only=True)
        _voice_cache[voice] = v
        return v
    return voice  # fallback to string

class KokoroTTS:
    def speak(self, text: str, voice: str = "af_bella", speed: float = 1.1):
        if not KOKORO_AVAILABLE:
            import subprocess
            (subprocess.run(["say", text]) if platform.system() == "Darwin" else print(f"[TTS fallback] {text[:80]}"))
            return
        try:
            import numpy as np
            voicepack = _load_voice(voice)
            generator = _pipeline(text, voice=voicepack, speed=speed)
            chunks = [audio for _, _, audio in generator if audio is not None and len(audio) > 0]
            if chunks:
                full_audio = np.concatenate(chunks)
                try:
                    import scipy.signal as sps
                    device_info = sd.query_devices(sd.default.device[1])
                    target_sr = int(device_info["default_samplerate"])
                    if target_sr != 24000:
                        num_samples = int(len(full_audio) * target_sr / 24000)
                        full_audio = sps.resample(full_audio, num_samples)
                    sd.play(full_audio, samplerate=target_sr)
                except Exception:
                    sd.play(full_audio, samplerate=24000)
                sd.wait()
        except Exception as e:
            print(f"[KokoroTTS] speak error: {e}")
            import subprocess
            (subprocess.run(["say", text]) if platform.system() == "Darwin" else print(f"[TTS fallback] {text[:80]}"))

    def speak_async(self, text: str, voice: str = "af_bella"):
        threading.Thread(
            target=self.speak, args=(text, voice), daemon=True
        ).start()

_tts = KokoroTTS()

def speak(text: str):
    _tts.speak(text)

def speak_async(text: str):
    _tts.speak_async(text)

# ── Streaming TTS — speak sentence by sentence ──────────────────────────
import re

def speak_streaming(text_generator):
    """
    Takes a generator that yields text chunks.
    Speaks each complete sentence as soon as it arrives.
    First sentence plays in <200ms of generation start.
    """
    buffer = ""
    sentence_end = re.compile(r'([^.!?]*[.!?]+)\s*')

    for chunk in text_generator:
        buffer += chunk
        while True:
            match = sentence_end.match(buffer)
            if not match:
                break
            sentence = match.group(1).strip()
            buffer   = buffer[match.end():]
            if len(sentence) > 3:
                _tts.speak(sentence)

    # Speak any remaining text
    if buffer.strip() and len(buffer.strip()) > 3:
        _tts.speak(buffer.strip())
