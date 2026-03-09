import threading, os, sys
import warnings
warnings.filterwarnings("ignore")

_BASE   = os.path.dirname(os.path.abspath(__file__))
_MODEL  = os.path.join(_BASE, "kokoro-v1_0.pth")
_VOICES = os.path.join(_BASE, "voices")

try:
    from kokoro import KPipeline
    import sounddevice as sd
    import torch

    _pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M', model=_MODEL)

    # Pre-load default voice into memory at startup
    _voice_cache = {}
    _default_voice_path = os.path.join(_VOICES, "af_bella.pt")
    if os.path.exists(_default_voice_path):
        _voice_cache["af_bella"] = torch.load(_default_voice_path, weights_only=True)

    KOKORO_AVAILABLE = True
    print("[KokoroTTS] ✅ Kokoro v1 ready")
except Exception as e:
    print(f"[KokoroTTS] Not available ({e}) — falling back to macOS say")
    KOKORO_AVAILABLE = False

def _load_voice(voice: str):
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
            subprocess.run(["say", text])
            return
        try:
            voicepack = _load_voice(voice)
            generator = _pipeline(text, voice=voicepack, speed=speed)
            for _, _, audio in generator:
                if audio is not None and len(audio) > 0:
                    sd.play(audio, samplerate=24000)
                    sd.wait()
        except Exception as e:
            print(f"[KokoroTTS] speak error: {e}")
            import subprocess
            subprocess.run(["say", text])

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
