import threading, os

_BASE = os.path.dirname(os.path.abspath(__file__))

try:
    from kokoro import KPipeline
    import sounddevice as sd
    import numpy as np

    _pipeline = KPipeline(lang_code='a')  # 'a' = American English
    KOKORO_AVAILABLE = True
    print("[KokoroTTS] ✅ Kokoro v1 loaded")
except Exception as e:
    print(f"[KokoroTTS] Not available ({e}) — falling back to macOS say")
    KOKORO_AVAILABLE = False

class KokoroTTS:
    def speak(self, text: str, voice: str = "af_bella", speed: float = 1.1):
        if not KOKORO_AVAILABLE:
            import subprocess
            subprocess.run(["say", text])
            return
        try:
            generator = _pipeline(text, voice=voice, speed=speed)
            for _, _, audio in generator:
                sd.play(audio, samplerate=24000)
                sd.wait()
        except Exception as e:
            print(f"[KokoroTTS] speak error: {e}")
            import subprocess
            subprocess.run(["say", text])

    def speak_async(self, text: str):
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()

_tts = KokoroTTS()

def speak(text: str):
    _tts.speak(text)

def speak_async(text: str):
    _tts.speak_async(text)
