# ==========================================
# vision/vision_engine.py
# JARVIS Vision Orchestrator
# ==========================================

import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOTS_DIR = os.path.join(_BACKEND_DIR, "data", "snapshots")


class VisionEngine:

    def __init__(self):
        self._last_screen_hash = None
        self._last_camera_hash = None
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
        logger.info("👁️ Vision engine initialized")

    # ── Screen ────────────────────────────────────────────────

    def analyze_screen(self, user_context: str = "") -> Dict:
        """Capture and analyze current screen."""
        from vision.capture import capture_screen
        from vision.analyzer import analyze

        b64 = capture_screen()
        if not b64:
            return {"error": "Screen capture failed", "jarvis_response": "Can't capture screen right now."}

        # Detect changes
        changed = self._check_changed(b64, "screen")
        result = analyze(b64, mode="screen", user_context=user_context)
        result["screen_changed"] = changed

        # Save snapshot
        self._save_snapshot(b64, "screen")
        return result

    # ── Camera ────────────────────────────────────────────────

    def analyze_camera(self, user_context: str = "") -> Dict:
        """Capture and analyze camera frame."""
        from vision.capture import capture_camera
        from vision.analyzer import analyze

        b64 = capture_camera()
        if not b64:
            return {"error": "Camera capture failed", "jarvis_response": "Can't access camera. Check permissions in System Settings → Privacy → Camera."}

        changed = self._check_changed(b64, "camera")
        result = analyze(b64, mode="camera", user_context=user_context)
        result["scene_changed"] = changed

        self._save_snapshot(b64, "camera")
        return result

    # ── Image file ────────────────────────────────────────────

    def analyze_image(self, image_path: str, user_context: str = "") -> Dict:
        """Analyze an image file."""
        from vision.capture import image_file_to_base64
        from vision.analyzer import analyze

        b64 = image_file_to_base64(image_path)
        if not b64:
            return {"error": f"Cannot read image: {image_path}"}

        return analyze(b64, mode="image", user_context=user_context)

    # ── Watch mode ────────────────────────────────────────────

    def watch_screen(self, interval: int = 10, callback=None):
        """Continuously monitor screen for changes."""
        import threading
        import time

        def _loop():
            logger.info(f"👁️ Screen watch mode started (every {interval}s)")
            while self._watching:
                result = self.analyze_screen()
                if result.get("screen_changed") and callback:
                    callback(result)
                time.sleep(interval)

        self._watching = True
        thread = threading.Thread(target=_loop, daemon=True)
        thread.start()
        return thread

    def stop_watch(self):
        self._watching = False
        logger.info("🛑 Screen watch stopped")

    # ── Helpers ───────────────────────────────────────────────

    def _check_changed(self, b64: str, source: str) -> bool:
        """Check if image changed since last capture."""
        import hashlib
        h = hashlib.md5(b64[:1000].encode()).hexdigest()
        attr = f"_last_{source}_hash"
        last = getattr(self, attr, None)
        setattr(self, attr, h)
        return last != h

    def _save_snapshot(self, b64: str, source: str):
        """Save latest snapshot."""
        from vision.capture import save_base64_image
        path = os.path.join(SNAPSHOTS_DIR, f"last_{source}.jpg")
        save_base64_image(b64, path)


# Singleton
vision_engine = VisionEngine()