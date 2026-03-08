import threading

try:
    from kokoro_onnx import Kokoro
    import sounddevice as sd
    import os
    _base = os.path.dirname(os.path.abspath(__file__))
    _model = Kokoro(
        os.path.join(_base, "kokoro-v0_19.onnx"),
        os.path.join(_base, "voices.bin")
    )
    KOKORO_AVAILABLE = True
except Exception as e:
    print(f"[KokoroTTS] Not available ({e}) — falling back to macOS say")
    KOKORO_AVAILABLE = False

class KokoroTTS:
    def speak(self, text: str, voice: str = "af_bella", speed: float = 1.1):
        if not KOKORO_AVAILABLE:
            import subprocess
            subprocess.run(["say", text])
            return
        samples, sample_rate = _model.create(text, voice=voice, speed=speed)
        sd.play(samples, sample_rate)
        sd.wait()

    def speak_async(self, text: str):
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()

# ── Module-level functions so `from tts_kokoro import speak` works ──────
_tts = KokoroTTS()

def speak(text: str):
    _tts.speak(text)

def speak_async(text: str):
    _tts.speak_async(text)
