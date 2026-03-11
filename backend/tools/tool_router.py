# ==========================================
# tools/tool_router.py
# ==========================================

from .file_reader import read_file
from .api_caller  import call_api

TOOLS             = ["file_reader", "system_monitor", "task_manager", "git", "python_sandbox", "screen_watcher", "smart_home", "device_discovery", "system_controller"]
APPROVAL_REQUIRED = ["git", "python_sandbox"]

FILE_TRIGGERS = [
    "read ", "open file", "show file", "read file",
    "cat ", "view file", "load file", "contents of"
]

SYSTEM_MONITOR_TRIGGERS = [
    "cpu", "ram", "memory usage", "disk", "system stats",
    "system load", "machine performance", "how slow", "why slow",
    "performance", "usage", "processes", "running apps",
    "how much memory", "how much cpu", "system info"
]

TASK_TRIGGERS = [
    "add task", "new task", "my tasks", "show tasks",
    "list tasks", "remind me", "todo", "to do",
    "complete task", "finish task", "task list",
    "pending task", "see tasks", "view tasks", "what are my tasks"
]

GIT_TRIGGERS = [
    "git status", "git log", "git commit", "git branch",
    "git diff", "what changed", "show commits", "git info"
]

PYTHON_TRIGGERS = [
    "```python", "run python", "execute python",
    "run this code", "run code", "execute code",
    "run script", "python script"
]

SYSTEM_CONTROL_TRIGGERS = [
    "open app", "close app", "quit app", "launch app",
    "play music", "pause music", "skip song",
    "next song", "previous song",
    "volume up", "volume down", "mute", "unmute",
    "take screenshot", "lock screen",
    "sleep display", "empty trash"
]

SCREEN_TRIGGERS = [
    "what's on my screen", "whats on my screen",
    "what am i working on", "look at my screen",
    "read my screen", "what does my screen show",
    "screen analysis", "analyze my screen",
    "screen error", "error on screen"
]

DEVICE_TRIGGERS = [
    "turn on", "turn off", "switch on", "switch off",
    "dim the", "brighten the", "set brightness", "set color",
    "lock the", "unlock the", "scan devices", "what devices",
    "show devices", "connect to", "camera feed", "thermostat",
    "robot vacuum", "smart home", "home assistant"
]


def detect_tool(user_input: str) -> str | None:
    text = user_input.lower()

    if any(t in text for t in SCREEN_TRIGGERS):
        return "screen_watcher"
    if any(t in text for t in ["scan devices", "what devices", "show devices", "find devices"]):
        return "device_discovery"
    if any(t in text for t in DEVICE_TRIGGERS):
        return "smart_home"
    if any(t in text for t in PYTHON_TRIGGERS):
        return "python_sandbox"
    if any(t in text for t in GIT_TRIGGERS):
        return "git"
    if any(t in text for t in TASK_TRIGGERS):
        return "task_manager"
    if any(t in text for t in SYSTEM_MONITOR_TRIGGERS):
        return "system_monitor"
    if any(t in text for t in FILE_TRIGGERS):
        return "file_reader"
    from tools.system_controller import is_system_command
    if is_system_command(text):
        return "system_controller"

    return None


def is_system_command(text: str) -> bool:
    return any(t in text.lower() for t in SYSTEM_CONTROL_TRIGGERS)


def requires_approval(tool: str) -> bool:
    return tool in APPROVAL_REQUIRED


def route_tool(user_text: str):
    text = user_text.lower()
    if text.startswith("read "):
        return read_file(user_text.replace("read ", "").strip())
    if text.startswith("api "):
        return call_api(user_text.replace("api ", "").strip())

    tool = detect_tool(user_text)

    if tool == "screen_watcher":
        try:
            from vision.screen_watcher import ScreenWatcher
            return ScreenWatcher().capture_and_analyze(user_text)
        except Exception as e:
            return f"Screen watcher error: {e}"

    if tool == "smart_home":
        try:
            from tools.smart_home import SmartHome
            sh = SmartHome()
            t  = user_text.lower()
            if "turn on" in t or "switch on" in t:
                entity = _extract_entity(t)
                sh.control_light(entity, True)
                return f"Turned on {entity}."
            if "turn off" in t or "switch off" in t:
                entity = _extract_entity(t)
                sh.control_light(entity, False)
                return f"Turned off {entity}."
            if "lock" in t:
                entity = _extract_entity(t)
                sh.lock_door(entity)
                return f"Locked {entity}."
            if "unlock" in t:
                entity = _extract_entity(t)
                sh.unlock_door(entity)
                return f"Unlocked {entity}."
            entities = sh.get_all_entities()
            return f"Smart home has {len(entities)} entities connected."
        except Exception as e:
            return f"Smart home error: {e}"

    if tool == "device_discovery":
        try:
            from tools.device_discovery import DeviceDiscovery
            devices = DeviceDiscovery().scan_all()
            if not devices:
                return "No devices found on network."
            names = list(devices.keys())[:10]
            return f"Found {len(devices)} devices: {', '.join(names)}"
        except Exception as e:
            return f"Device discovery error: {e}"

    return None


def _extract_entity(text: str) -> str:
    """Best-effort entity extraction from natural language command."""
    stopwords = ["turn", "on", "off", "switch", "the", "my", "please",
                 "lock", "unlock", "dim", "brighten"]
    words = [w for w in text.split() if w not in stopwords]
    entity_name = "_".join(words[:3]) if words else "light"
    return f"light.{entity_name}"
