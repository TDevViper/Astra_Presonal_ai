from collections import deque
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FrameBuffer:
    def __init__(self, maxlen: int = 10):
        self.frames     = deque(maxlen=maxlen)
        self.timestamps = deque(maxlen=maxlen)

    def add(self, frame_b64: str):
        self.frames.append(frame_b64)
        self.timestamps.append(datetime.now().isoformat())

    def get_context_prompt(self) -> str:
        n = len(self.frames)
        return (
            f"You have seen {n} frames over the last {n * 8} seconds. "
            "Describe what changed since the first frame."
        )

    def detect_motion(self) -> bool:
        if len(self.frames) < 2:
            return False
        try:
            import cv2, numpy as np, base64

            def decode(b64):
                data = base64.b64decode(b64)
                arr  = np.frombuffer(data, dtype=np.uint8)
                return cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)

            diff = cv2.absdiff(decode(self.frames[-2]), decode(self.frames[-1]))
            return float(diff.mean()) > 15
        except Exception as e:
            logger.warning(f"Motion detection failed: {e}")
            return False

    def latest(self):
        return self.frames[-1] if self.frames else None
