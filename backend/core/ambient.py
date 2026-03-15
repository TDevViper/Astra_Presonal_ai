# core/ambient.py
# ASTRA Ambient Awareness — watches screen + system continuously
# Injects live context into every prompt automatically
import threading, time, logging, os
from typing import Optional, Dict

logger = logging.getLogger(__name__)

_SCAN_INTERVAL = 60          # seconds between ambient scans
_ERROR_SCAN_INTERVAL = 15    # faster scan when errors detected

_live_context: Dict = {
    "active_app":     None,
    "screen_summary": None,
    "error_detected": False,
    "error_text":     None,
    "last_scan":      None,
    "cpu_alert":      False,
}
_broadcast_fn = None
_running       = False


def set_broadcast(fn):
    global _broadcast_fn
    _broadcast_fn = fn


def get_live_context() -> Dict:
    return dict(_live_context)


def get_context_string() -> str:
    """Returns a short string to inject into system prompts."""
    c = _live_context
    if not c["screen_summary"] and not c["active_app"]:
        return ""
    parts = []
    if c["active_app"]:
        parts.append(f"Active app: {c['active_app']}")
    if c["screen_summary"]:
        parts.append(f"Screen: {c['screen_summary']}")
    if c["error_detected"] and c["error_text"]:
        parts.append(f"⚠️ Error on screen: {c['error_text'][:100]}")
    return " | ".join(parts)


def _scan_once():
    global _live_context
    try:
        # Screen capture + LLaVA analysis
        from vision.screen_watcher import ScreenWatcher
        sw = ScreenWatcher()

        # What app + what's happening
        summary = sw.capture_and_analyze(
            "In one sentence: what app is open and what is the user doing?"
        )
        _live_context["screen_summary"] = summary
        _live_context["last_scan"] = time.time()

        # Extract active app name
        import subprocess
        app_result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=3
        )
        if app_result.returncode == 0:
            _live_context["active_app"] = app_result.stdout.strip()

        # Error detection
        error_detected = sw.detect_error_on_screen()
        _live_context["error_detected"] = error_detected

        if error_detected:
            error_text = sw.capture_and_analyze(
                "Extract the exact error message text from the screen. Just the error, nothing else."
            )
            _live_context["error_text"] = error_text
            logger.info("🚨 Ambient: error detected — %s", error_text[:60])
            if _broadcast_fn:
                _broadcast_fn(
                    f"⚠️ I noticed an error on your screen: {error_text[:80]}. "
                    f"Want me to debug it?"
                )
            try:
                from core.visual_memory import store_vision_episode
                store_vision_episode(error_text, source="screen",
                                     error_detected=True,
                                     active_app=_live_context.get("active_app"))
            except Exception:
                pass
        else:
            _live_context["error_text"] = None
            # Store normal screen observation in visual memory
            if summary and len(summary) > 10:
                try:
                    from core.visual_memory import store_vision_episode
                    store_vision_episode(summary, source="screen",
                                         active_app=_live_context.get("active_app"))
                except Exception:
                    pass

    except Exception as e:
        logger.debug("ambient scan skipped: %s", e)


def _ambient_loop():
    while _running:
        _scan_once()
        # Scan faster if error was detected
        interval = _ERROR_SCAN_INTERVAL if _live_context["error_detected"] else _SCAN_INTERVAL
        time.sleep(interval)


def start_ambient(broadcast_fn=None):
    global _running, _broadcast_fn
    if broadcast_fn:
        _broadcast_fn = broadcast_fn
    if _running:
        return
    _running = True
    t = threading.Thread(target=_ambient_loop, daemon=True)
    t.start()
    logger.info("👁️  Ambient awareness started (interval=%ds)", _SCAN_INTERVAL)


def stop_ambient():
    global _running
    _running = False
