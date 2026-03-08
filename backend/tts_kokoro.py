import os
import warnings
import tempfile
warnings.filterwarnings("ignore")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _get_provider():
    return os.getenv("TTS_PROVIDER", "pyttsx3").lower()

def speak(text: str):
    provider = _get_provider()
    if provider == "kokoro":
        _speak_kokoro(text)
    elif provider == "elevenlabs":
        _speak_elevenlabs(text)
    else:
        _speak_pyttsx3(text)

def _speak_kokoro(text: str):
    try:
        from kokoro import KPipeline
        import numpy as np
        import scipy.io.wavfile as wav

        voice = os.getenv("KOKORO_VOICE", "am_michael")
        pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
        generator = pipeline(text, voice=voice, speed=1.0)

        # Collect all audio chunks
        chunks = []
        for gs, ps, audio in generator:
            chunks.append(np.array(audio))

        if not chunks:
            raise RuntimeError("Kokoro generated no audio chunks")

        # Concatenate and write to temp wav
        full_audio = np.concatenate(chunks)
        full_audio_int16 = np.clip(full_audio * 32767 * 3.0, -32767, 32767).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        wav.write(tmp_path, 24000, full_audio_int16)

        # Play via afplay — respects macOS audio routing (speakers/headphones)
        os.system(f"afplay {tmp_path}")
        os.unlink(tmp_path)

    except Exception as e:
        print("[TTS] Kokoro error: " + str(e) + ", falling back to pyttsx3")
        _speak_pyttsx3(text)

def _speak_pyttsx3(text: str):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", int(os.getenv("VOICE_RATE", "175")))
        engine.setProperty("volume", float(os.getenv("VOICE_VOLUME", "1.0")))
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("[TTS] pyttsx3 error: " + str(e))

def _speak_elevenlabs(text: str):
    try:
        import requests, io, soundfile as sf
        import scipy.io.wavfile as wav
        import numpy as np
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY not set")
        resp = requests.post(
            "https://api.elevenlabs.io/v1/text-to-speech/" + voice_id,
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_monolingual_v1"},
            timeout=15
        )
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(resp.content)
            tmp_path = f.name
        os.system(f"afplay {tmp_path}")
        os.unlink(tmp_path)
    except Exception as e:
        print("[TTS] ElevenLabs error: " + str(e) + ", falling back to pyttsx3")
        _speak_pyttsx3(text)
