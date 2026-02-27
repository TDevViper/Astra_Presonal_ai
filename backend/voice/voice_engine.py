import logging
import threading
import requests

logger = logging.getLogger(__name__)

ASTRA_API = "http://127.0.0.1:5050"


class VoiceEngine:

    def __init__(self):
        self.is_listening = False
        self.is_speaking = False
        self.wake_detector = None
        self._mode = "idle"  # idle | wake_word | push_to_talk

    # ── Start / Stop ─────────────────────────────────────────

    def start_wake_word_mode(self):
        """Continuously listen for 'Hey ASTRA' then respond."""
        from voice.wake_word import WakeWordDetector
        self._mode = "wake_word"
        self.wake_detector = WakeWordDetector(on_wake=self._on_wake)
        self.wake_detector.start()
        logger.info("🚀 Voice engine started in wake word mode")

    def start_push_to_talk(self, duration: int = 5):
        """Single push-to-talk recording."""
        self._mode = "push_to_talk"
        thread = threading.Thread(target=self._ptt_cycle, args=(duration,), daemon=True)
        thread.start()
        return thread

    def stop(self):
        if self.wake_detector:
            self.wake_detector.stop()
        self._mode = "idle"
        self.is_listening = False
        logger.info("🛑 Voice engine stopped")

    # ── Core Flow ─────────────────────────────────────────────

    def _on_wake(self):
        """Called when wake word detected."""
        from voice.speaker import speak
        from voice.listener import listen

        speak("Yeah?", use_macos=True)

        self.is_listening = True
        user_text = listen(duration=5)
        self.is_listening = False

        if not user_text.strip():
            speak("I didn't catch that.", use_macos=True)
            return

        logger.info(f"🎤 Heard: {user_text}")
        reply = self._send_to_astra(user_text)
        
        self.is_speaking = True
        speak(reply, use_macos=True)
        self.is_speaking = False

    def _ptt_cycle(self, duration: int):
        """Push-to-talk single cycle."""
        from voice.speaker import speak
        from voice.listener import listen

        self.is_listening = True
        logger.info(f"🎤 Listening for {duration}s...")
        user_text = listen(duration=duration)
        self.is_listening = False

        if not user_text.strip():
            return

        logger.info(f"🎤 Heard: {user_text}")
        reply = self._send_to_astra(user_text)

        self.is_speaking = True
        speak(reply, use_macos=True)
        self.is_speaking = False

    def _send_to_astra(self, text: str) -> str:
        """Send text to ASTRA API and get reply."""
        try:
            res = requests.post(
                f"{ASTRA_API}/chat",
                json={"message": text},
                timeout=30
            )
            data = res.json()
            return data.get("reply", "Sorry, I couldn't process that.")
        except Exception as e:
            logger.error(f"❌ API error: {e}")
            return "I can't reach my brain right now."

    def get_status(self) -> dict:
        return {
            "mode": self._mode,
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking,
        }


# Singleton
voice_engine = VoiceEngine()
