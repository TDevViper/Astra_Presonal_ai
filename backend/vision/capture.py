# ==========================================
# vision/capture.py
# Screen capture + Camera capture
# ==========================================

import base64
import logging
import os
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)


def capture_screen(monitor: int = 1) -> Optional[str]:
    """Capture screen and return base64 encoded image."""
    try:
        import mss
        from PIL import Image

        with mss.mss() as sct:
            mon = sct.monitors[monitor]
            screenshot = sct.grab(mon)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # Resize to reasonable size for LLaVA (max 1280px wide)
            max_w = 800
            if img.width > max_w:
                ratio = max_w / img.width
                img = img.resize((max_w, int(img.height * ratio)))

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=60)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            logger.info(f"📸 Screen captured ({img.width}x{img.height})")
            return encoded

    except Exception as e:
        logger.error(f"❌ Screen capture error: {e}")
        return None


def capture_camera(camera_index: int = 1, save_path: Optional[str] = None) -> Optional[str]:
    """Capture single frame from camera and return base64 encoded image."""
    try:
        import cv2

        # Try camera_index first, fallback to other
        # Try camera_index first, fallback to other
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            alt = 1 if camera_index == 0 else 0
            cap = cv2.VideoCapture(alt)
        if not cap.isOpened():
            alt = 1 if camera_index == 0 else 0
            cap = cv2.VideoCapture(alt)
        if not cap.isOpened():
            logger.error("❌ Cannot open camera")
            return None

        # Set resolution and focus
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

        # Warm up camera properly
        import time
        for _ in range(30):
            cap.read()
        time.sleep(1.5)

        ret, frame = cap.read()
        cap.release()

        if not ret:
            logger.error("❌ Failed to capture frame")
            return None

        # Save if path given
        if save_path:
            cv2.imwrite(save_path, frame)

        # Encode to base64
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        encoded = base64.b64encode(buffer).decode("utf-8")
        logger.info(f"📷 Camera frame captured")
        return encoded

    except Exception as e:
        logger.error(f"❌ Camera capture error: {e}")
        return None


def image_file_to_base64(path: str) -> Optional[str]:
    """Convert image file to base64."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"❌ File read error: {e}")
        return None


def save_base64_image(b64: str, path: str) -> bool:
    """Save base64 image to file."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True
    except Exception as e:
        logger.error(f"❌ Save error: {e}")
        return False