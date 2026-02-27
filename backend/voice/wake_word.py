import logging
import numpy as np
import sounddevice as sd
import threading

logger = logging.getLogger(__name__)

WAKE_WORDS = ["hey astra", "astra", "hey astra!"]
SAMPLE_RATE = 16000
CHUNK_DURATION = 0.5   # seconds per chunk
ENERGY_THRESHOLD = 0.02


class WakeWordDetector:

    def __init__(self, on_wake=None):
        self.on_wake = on_wake  # callback when wake word detected
        self._running = False
        self._thread = None

    def _check_wake_word(self, audio: np.ndarray) -> bool:
        """Check audio for wake word using whisper."""
        from voice.listener import transcribe, is_silent

        if is_silent(audio, threshold=ENERGY_THRESHOLD):
            return False

        try:
            text = transcribe(audio).lower()
            return any(w in text for w in WAKE_WORDS)
        except Exception:
            return False

    def _listen_loop(self):
        """Continuously listen for wake word."""
        logger.info("👂 Wake word detector started — say 'Hey ASTRA'")
        chunk_size = int(SAMPLE_RATE * 1.5)  # 1.5s chunks for wake word

        while self._running:
            try:
                audio = sd.rec(chunk_size, samplerate=SAMPLE_RATE,
                               channels=1, dtype="float32")
                sd.wait()
                audio = audio.flatten()

                if self._check_wake_word(audio):
                    logger.info("🎯 Wake word detected!")
                    if self.on_wake:
                        self.on_wake()

            except Exception as e:
                logger.error(f"Wake word error: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        logger.info("🛑 Wake word detector stopped")