import mss
import base64
import io
from PIL import Image


class ScreenWatcher:
    def capture_and_analyze(self, question: str = None) -> str:
        from vision.llava_analyzer import analyze_image

        with mss.mss() as sct:
            screenshot = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            img.thumbnail((1280, 720))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            b64 = base64.b64encode(buf.getvalue()).decode()
        prompt = (
            question
            or "What application is open and what is the user working on? One sentence."
        )
        return analyze_image(b64, prompt)

    def detect_error_on_screen(self) -> bool:
        result = self.capture_and_analyze(
            "Is there an error, crash, or warning visible on screen? Answer only yes or no."
        )
        return "yes" in result.lower()
