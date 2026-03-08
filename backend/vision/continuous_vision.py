import threading
import time
import logging

logger = logging.getLogger(__name__)


class ContinuousVision:
    def __init__(self, broadcast_fn, interval: int = 8):
        self.broadcast      = broadcast_fn
        self.interval       = interval
        self.last_desc      = ""
        self.running        = False
        self._latest_frame  = None

    def set_frame(self, frame_b64: str):
        self._latest_frame = frame_b64

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("👁️ ContinuousVision started")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                if self._latest_frame:
                    from vision.analyzer import analyze
                    result = analyze(
                        self._latest_frame,
                        mode="camera",
                        user_context="Describe only what changed. One sentence."
                    )
                    desc = result.get("jarvis_response", "") or result.get("summary", "")
                    if desc and self._is_significant_change(desc):
                        self.broadcast(f"👁️ {desc}")
                        self.last_desc = desc
            except Exception as e:
                logger.error(f"ContinuousVision error: {e}")
            time.sleep(self.interval)

    def _is_significant_change(self, new_desc: str) -> bool:
        if not self.last_desc:
            return True
        old_words = set(self.last_desc.lower().split())
        new_words = set(new_desc.lower().split())
        overlap   = len(old_words & new_words) / max(len(old_words), 1)
        return overlap < 0.6
