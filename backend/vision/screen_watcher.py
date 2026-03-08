import base64
import io
import logging

logger = logging.getLogger(__name__)


class ScreenWatcher:
    def capture_and_analyze(self, question: str = None) -> dict:
        try:
            import mss
            from PIL import Image
            from vision.analyzer import analyze

            with mss.mss() as sct:
                screenshot = sct.grab(sct.monitors[1])
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                img.thumbnail((1280, 720))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=75)
                b64 = base64.b64encode(buf.getvalue()).decode()

            context = question or "What application is open and what is the user working on?"
            return analyze(b64, mode="screen", user_context=context)

        except ImportError as e:
            return {"error": f"Missing: {e}", "jarvis_response": "Screen capture unavailable."}
        except Exception as e:
            logger.error(f"ScreenWatcher error: {e}")
            return {"error": str(e), "jarvis_response": "Screen capture failed."}

    def detect_error_on_screen(self) -> bool:
        result = self.capture_and_analyze(
            "Is there an error, crash, or warning visible? Answer only yes or no."
        )
        resp = result.get("jarvis_response", "") or result.get("summary", "")
        return "yes" in resp.lower()

    def whats_on_screen(self) -> str:
        result = self.capture_and_analyze()
        return result.get("jarvis_response", result.get("summary", "Nothing detected"))
