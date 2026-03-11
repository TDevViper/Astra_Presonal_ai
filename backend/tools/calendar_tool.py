import subprocess
import logging
import platform

logger = logging.getLogger(__name__)

IS_MACOS = platform.system() == "Darwin"


def _run_osascript(script):
    if not IS_MACOS:
        return None
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        logger.debug(f"osascript not available: {e}")
        return None


def handle_calendar_command(user_input):
    text = user_input.lower()
    if not any(w in text for w in ["calendar", "schedule", "reminder", "event", "meeting"]):
        return None
    if not IS_MACOS:
        return "Calendar integration requires macOS. Running in Docker mode — calendar unavailable."
    return None


def morning_briefing_text():
    if not IS_MACOS:
        return ""
    try:
        script = 'tell application "Calendar" to get summary of events of calendar "Home"'
        result = _run_osascript(script)
        return result or ""
    except Exception:
        return ""


def reminder_check_text(user_name=None):
    if not IS_MACOS:
        return ""
    try:
        script = 'tell application "Reminders" to get name of reminders'
        result = _run_osascript(script)
        return result or ""
    except Exception:
        return ""
