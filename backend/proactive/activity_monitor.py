# ==========================================
# proactive/activity_monitor.py
# Monitors keyboard, mouse, screen, webcam
# and tells ASTRA when to speak naturally
# ==========================================

import logging
import threading
import time
import subprocess
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)

USER_NAME = "User"  # loaded from memory at runtime

THRESHOLDS = {
    "coding":   90 * 60,
    "browsing": 45 * 60,
    "watching": 40 * 60,
    "reading":  60 * 60,
    "unknown":  60 * 60,
}

POSTURE_CHECK_INTERVAL  = 20 * 60   # every 20 mins
SCREEN_CHECK_INTERVAL   = 5  * 60   # every 5 mins

APP_MAP = {
    "xcode": "coding", "cursor": "coding", "vscode": "coding",
    "code": "coding", "pycharm": "coding", "terminal": "coding",
    "iterm": "coding", "warp": "coding", "electron": "coding",
    "safari": "browsing", "chrome": "browsing", "firefox": "browsing",
    "arc": "browsing",
    "youtube": "watching", "netflix": "watching", "vlc": "watching",
    "quicktime": "watching", "iina": "watching",
    "notion": "reading", "obsidian": "reading", "books": "reading",
    "kindle": "reading",
}


class ActivityMonitor:
    def __init__(self, speak_fn: Callable[[str], None], proactive_engine=None):
        self.speak             = speak_fn
        self.proactive         = proactive_engine
        self._running          = False

        self._activity_start   = datetime.now()
        self._last_input       = datetime.now()
        self._current_app      = "unknown"
        self._activity_type    = "unknown"
        self._last_spoke       = None
        self._last_posture     = datetime.now()
        self._last_screen      = datetime.now()
        self._last_screen_hash = None
        self._input_listener   = None

        logger.info("👁️ ActivityMonitor initialized")

    def start(self):
        if self._running:
            return
        self._running = True
        self._start_input_listener()
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
        logger.info("🚀 ActivityMonitor started")

    def stop(self):
        self._running = False
        if self._input_listener:
            self._input_listener.stop()

    # ── Input Listener ────────────────────────────────────────

    def _start_input_listener(self):
        try:
            from pynput import mouse, keyboard

            def on_activity(*args, **kwargs):
                now  = datetime.now()
                idle = (now - self._last_input).seconds
                if idle > 300:
                    self._activity_start = now
                    logger.info("⏱️ Activity reset after idle")
                self._last_input = now

            mouse.Listener(on_move=on_activity, on_click=on_activity, on_scroll=on_activity).start()
            keyboard.Listener(on_press=on_activity).start()
            logger.info("🖱️ Input listeners active")
        except Exception as e:
            logger.error(f"Input listener error: {e}")

    # ── Main Loop ─────────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                self._update_app()
                self._check_activity()
                self._check_posture()
                self._check_screen()
            except Exception as e:
                logger.error(f"ActivityMonitor error: {e}")
            time.sleep(120)  # M4 optimized

    # ── App Detection ─────────────────────────────────────────

    def _update_app(self):
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first process whose frontmost is true'],
                capture_output=True, text=True, timeout=3
            )
            app_name = result.stdout.strip().lower()
            if app_name and app_name != self._current_app:
                self._current_app  = app_name
                self._activity_type = self._classify_app(app_name)
                logger.info(f"📱 App: {app_name} → {self._activity_type}")
        except Exception:
            pass  # TODO: handle

    def _classify_app(self, app_name: str) -> str:
        for key, activity in APP_MAP.items():
            if key in app_name:
                return activity
        return "unknown"

    # ── Activity Check ────────────────────────────────────────

    def _check_activity(self):
        now       = datetime.now()
        idle      = (now - self._last_input).seconds
        elapsed   = (now - self._activity_start).seconds

        if idle > 300:
            return

        threshold = THRESHOLDS.get(self._activity_type, THRESHOLDS["unknown"])

        if self._last_spoke:
            if (now - self._last_spoke).seconds < 30 * 60:
                return

        if elapsed >= threshold:
            self._last_spoke     = now
            self._activity_start = now
            self._speak_break_suggestion(elapsed, self._activity_type)

    def _speak_break_suggestion(self, elapsed_seconds: int, activity: str):
        import random
        mins = elapsed_seconds // 60
        messages = {
            "coding": [
                f"Hey {USER_NAME}, you've been coding for {mins} minutes straight. Step away, your brain needs a reset.",
                f"{USER_NAME}, {mins} minutes of deep work. Close the laptop, walk around for 5 minutes.",
                f"Solid focus {USER_NAME} — {mins} minutes coding. Time to stand up and stretch.",
            ],
            "browsing": [
                f"Hey {USER_NAME}, you've been browsing for {mins} minutes. Maybe time to get up?",
                f"{USER_NAME}, {mins} minutes online. Stand up, grab some water.",
            ],
            "watching": [
                f"Hey {USER_NAME}, {mins} minutes of screen time. Give your eyes a break.",
                f"{USER_NAME}, you've been watching for {mins} minutes. Stand up, stretch your legs.",
            ],
            "reading": [
                f"{USER_NAME}, {mins} minutes of reading. Look away from the screen, rest your eyes.",
            ],
            "unknown": [
                f"Hey {USER_NAME}, you've been at it for {mins} minutes. Time for a quick break.",
            ],
        }
        msg = random.choice(messages.get(activity, messages["unknown"]))
        self.speak(msg)
        logger.info(f"💬 Break suggestion: {activity} {mins}mins")

    # ── Posture Check ─────────────────────────────────────────

    def _check_posture(self):
        now     = datetime.now()
        elapsed = (now - self._last_posture).seconds
        if elapsed < POSTURE_CHECK_INTERVAL:
            return
        if (now - self._last_input).seconds > 300:
            return

        self._last_posture = now
        result = self._analyze_posture()

        if result == "bad":
            self.speak(f"Hey {USER_NAME}, sit up straight. Your posture looks off.")
        elif result == "too_close":
            self.speak(f"{USER_NAME}, you're too close to the screen. Lean back a bit.")

    def _analyze_posture(self) -> str:
        try:
            import cv2
            cap   = cv2.VideoCapture(1)  # Mac built-in camera
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return "unknown"

            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            ).detectMultiScale(gray, 1.05, 3, minSize=(80, 80))

            if len(faces) == 0:
                return "unknown"

            h, w       = frame.shape[:2]
            fx, fy, fw, fh = faces[0]
            face_ratio = fw / w
            face_y     = (fy + fh / 2) / h

            if face_ratio > 0.40:
                return "too_close"
            if face_y > 0.65:
                return "bad"
            return "good"
        except Exception as e:
            logger.error(f"Posture check error: {e}")
            return "unknown"

    # ── Screen Awareness ──────────────────────────────────────

    def _check_screen(self):
        return  # disabled on M4 Air — too heavy
        now     = datetime.now()
        elapsed = (now - self._last_screen).seconds

        if elapsed < SCREEN_CHECK_INTERVAL:
            return
        if (now - self._last_input).seconds > 300:
            return  # User idle, skip

        self._last_screen = now

        # Run in background so it doesn't block the loop
        thread = threading.Thread(target=self._analyze_screen_and_react, daemon=True)
        thread.start()

    def _analyze_screen_and_react(self):
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from vision.capture import capture_screen
            from vision.analyzer import analyze
            import hashlib

            b64 = capture_screen()
            if not b64:
                return

            # Only analyze if screen actually changed
            h = hashlib.md5(b64[:1000].encode()).hexdigest()
            if h == self._last_screen_hash:
                return
            self._last_screen_hash = h

            logger.info("📸 Screen changed — analyzing...")
            result = analyze(b64, mode="screen")

            self._react_to_screen(result)

        except Exception as e:
            logger.error(f"Screen analysis error: {e}")

    def _react_to_screen(self, result: dict):
        """Decide if and what to say based on screen analysis."""
        if not result:
            return

        # Don't speak if spoke recently
        now = datetime.now()
        if self._last_spoke and (now - self._last_spoke).seconds < 10 * 60:
            return

        content_type = result.get("content_type", "")
        extracted    = result.get("extracted", {})
        error        = extracted.get("error") if extracted else None
        suggestions  = result.get("suggestions", [])
        summary      = result.get("summary", "")

        # ── Error detected on screen ──────────────────────────
        if error:
            self._last_spoke = now
            self.speak(f"Hey {USER_NAME}, I see an error on your screen. {error[:120]}")
            if suggestions:
                time.sleep(1)
                self.speak(f"Suggestion: {suggestions[0]}")
            return

        # ── Terminal visible with output ───────────────────────
        if content_type == "terminal":
            key_text = extracted.get("key_text", "") if extracted else ""
            if any(w in key_text.lower() for w in ["error", "failed", "exception", "traceback"]):
                self._last_spoke = now
                self.speak(f"Looks like something failed in your terminal, {USER_NAME}. Want me to help debug?")
            return

        # ── Long file open in editor ───────────────────────────
        if content_type == "code" and suggestions:
            # Only speak if there's something actionable
            issue = result.get("issues", [])
            if issue:
                self._last_spoke = now
                self.speak(f"Hey {USER_NAME}, I noticed something in your code. {issue[0]}")


# ── Standalone test ───────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/Users/arnavyadav/Astra/backend")

    def speak_blocking(text):
        print(f"🔊 {text}")
        import platform; (subprocess.run(["say", "-v", "Samantha", "-r", "185", text]) if platform.system() == "Darwin" else print(f"[TTS] {text[:80]}"))

    print("👁️ Testing ActivityMonitor...")
    monitor = ActivityMonitor(speak_fn=speak_blocking)

    monitor._update_app()
    print(f"Current app: {monitor._current_app} → {monitor._activity_type}")

    print("📷 Testing posture...")
    posture = monitor._analyze_posture()
    print(f"Posture: {posture}")

    print("📸 Testing screen awareness...")
    monitor._analyze_screen_and_react()

    monitor._speak_break_suggestion(95 * 60, "coding")

    print("✅ Done")
