from collections import deque
import base64
import numpy as np
import cv2
from datetime import datetime


class FrameBuffer:
    def __init__(self, maxlen=10):
        self.frames = deque(maxlen=maxlen)
        self.timestamps = deque(maxlen=maxlen)

    def add(self, frame_b64: str):
        self.frames.append(frame_b64)
        self.timestamps.append(datetime.now().isoformat())

    def latest(self):
        return self.frames[-1] if self.frames else None

    def get_context_prompt(self) -> str:
        n = len(self.frames)
        return f"You have seen {n} recent frames over the last {n * 8} seconds. Describe what changed."

    def detect_motion(self) -> bool:
        if len(self.frames) < 2:
            return False
        try:
            f1 = self._decode(self.frames[-2])
            f2 = self._decode(self.frames[-1])
            diff = cv2.absdiff(f1, f2)
            return float(diff.mean()) > 15
        except Exception:
            return False

    def _decode(self, b64: str) -> np.ndarray:
        data = base64.b64decode(b64)
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
