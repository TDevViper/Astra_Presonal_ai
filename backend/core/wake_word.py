import os
import platform
import logging

logger = logging.getLogger(__name__)

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    logger.warning("pvporcupine not available — wake word disabled")

_listener_thread = None
_stop_event       = None

# ── Model registry ────────────────────────────────────────────────────────
# Keys match platform.system() + "_" + platform.machine() (lowercased)
# Drop new .ppn files into wake_models/ and add an entry here.
_WAKE_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "wake_models"
)

_PLATFORM_MODELS = {
    "darwin_arm64":  "Hey-ASTRA_en_mac_v4_0_0.ppn",   # macOS Apple Silicon
    "darwin_x86_64": "Hey-ASTRA_en_mac_v4_0_0.ppn",   # macOS Intel
    "linux_x86_64":  "Hey-ASTRA_en_linux_v4_0_0.ppn", # Linux x86 (generate at console.picovoice.ai)
    "linux_aarch64": "Hey-ASTRA_en_rpi_v4_0_0.ppn",   # Raspberry Pi / Linux ARM
    "windows_amd64": "Hey-ASTRA_en_windows_v4_0_0.ppn", # Windows
}


def _get_model_path() -> str | None:
    """
    Resolve the correct .ppn for the current platform.
    Priority:
      1. WAKE_WORD_MODEL env var (absolute path or filename in wake_models/)
      2. Auto-detect from _PLATFORM_MODELS registry
    Returns None if no model found, with a helpful log message.
    """
    # Manual override
    env_override = os.getenv("WAKE_WORD_MODEL", "")
    if env_override:
        if os.path.isabs(env_override) and os.path.exists(env_override):
            return env_override
        candidate = os.path.join(_WAKE_MODELS_DIR, env_override)
        if os.path.exists(candidate):
            return candidate
        logger.warning(f"WAKE_WORD_MODEL='{env_override}' not found — falling back to auto-detect")

    # Auto-detect
    system  = platform.system().lower()           # darwin / linux / windows
    machine = platform.machine().lower()          # arm64 / x86_64 / aarch64 / amd64
    key     = f"{system}_{machine}"

    model_file = _PLATFORM_MODELS.get(key)
    if not model_file:
        logger.warning(
            f"No wake word model registered for platform '{key}'. "
            f"Generate one at https://console.picovoice.ai and add it to wake_models/. "
            f"Known platforms: {', '.join(_PLATFORM_MODELS.keys())}"
        )
        return None

    path = os.path.join(_WAKE_MODELS_DIR, model_file)
    if not os.path.exists(path):
        logger.warning(
            f"Wake word model '{model_file}' not found in {_WAKE_MODELS_DIR}. "
            f"Download it from https://console.picovoice.ai and place it in wake_models/."
        )
        return None

    logger.info(f"Wake word model: {model_file} (platform: {key})")
    return path


def start_wake_word_listener(callback=None):
    global _listener_thread, _stop_event

    if not PORCUPINE_AVAILABLE:
        logger.info("Wake word listener skipped — pvporcupine not installed")
        return None

    api_key = os.getenv("PICOVOICE_API_KEY", "")
    if not api_key:
        logger.warning("PICOVOICE_API_KEY not set — wake word disabled")
        return None

    model_path = _get_model_path()
    if not model_path:
        return None

    try:
        import pvporcupine
        import sounddevice as sd
        import numpy as np
        import threading

        porcupine   = pvporcupine.create(access_key=api_key, keyword_paths=[model_path])
        _stop_event = threading.Event()

        def _listen():
            with sd.InputStream(
                samplerate=porcupine.sample_rate,
                channels=1, dtype="int16",
                blocksize=porcupine.frame_length
            ) as stream:
                logger.info("🎤 Wake word listener started — say 'Hey ASTRA'")
                while not _stop_event.is_set():
                    audio, _ = stream.read(porcupine.frame_length)
                    result    = porcupine.process(audio.flatten())
                    if result >= 0:
                        logger.info("✅ Wake word detected!")
                        if callback:
                            callback()
            porcupine.delete()

        _listener_thread = threading.Thread(target=_listen, daemon=True)
        _listener_thread.start()
        return _listener_thread

    except Exception as e:
        logger.warning(f"Wake word listener failed to start: {e}")
        return None


def stop_wake_word_listener():
    global _stop_event
    if _stop_event:
        _stop_event.set()
        logger.info("Wake word listener stopped")
