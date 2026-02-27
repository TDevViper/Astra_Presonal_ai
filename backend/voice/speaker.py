import logging
import pyttsx3
import subprocess
from typing import Any, List, Dict, cast

logger = logging.getLogger(__name__)

_engine = None


def get_engine() -> pyttsx3.Engine:
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        # Tune voice settings
        _engine.setProperty("rate", 185)     # speed
        _engine.setProperty("volume", 0.95)  # volume
        # Try to set a better voice
        voices = cast(List[Any], _engine.getProperty("voices"))  # ✅ Fix
        for voice in voices:
            if "samantha" in voice.name.lower() or "karen" in voice.name.lower():
                _engine.setProperty("voice", voice.id)
                break
        logger.info("🔊 TTS engine ready")
    return _engine


def speak(text: str, use_macos: bool = True) -> None:
    """Speak text aloud."""
    if not text or not text.strip():
        return

    # Clean text for speech
    clean = text.replace("*", "").replace("#", "").replace("```", "").strip()
    # Limit to reasonable length
    if len(clean) > 300:
        clean = clean[:300] + "..."

    logger.info(f"🔊 Speaking: {clean[:60]}...")

    if use_macos:
        # macOS 'say' command is more natural
        try:
            subprocess.run(["say", "-v", "Samantha", "-r", "185", clean], check=True)
            return
        except Exception:
            pass

    # Fallback to pyttsx3
    try:
        engine = get_engine()
        engine.say(clean)
        engine.runAndWait()
    except Exception as e:
        logger.error(f"❌ TTS error: {e}")


def speak_async(text: str) -> None:
    """Non-blocking speak using subprocess."""
    import threading
    thread = threading.Thread(target=speak, args=(text,), daemon=True)
    thread.start()


def list_voices() -> List[Dict[str, str]]:
    """List available voices."""
    engine = get_engine()
    voices = cast(List[Any], engine.getProperty("voices"))  # ✅ Fix
    return [{"id": v.id, "name": v.name} for v in voices]