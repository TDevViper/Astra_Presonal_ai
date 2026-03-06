# ==========================================
# tools/tool_router.py
# Semantic trigger matching — catches natural language
# ==========================================

from .file_reader import read_file
from .api_caller  import call_api

TOOLS            = ["file_reader", "system_monitor", "task_manager", "git", "python_sandbox"]
APPROVAL_REQUIRED = ["git", "python_sandbox"]

# Wide semantic triggers — catch natural language variations
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
    "complete task", "finish task", "task list"
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

# System CONTROL — apps, volume, screen
SYSTEM_CONTROL_TRIGGERS = [
    "open app", "close app", "quit app", "launch app",
    "play music", "pause music", "skip song",
    "next song", "previous song",
    "volume up", "volume down", "mute", "unmute",
    "take screenshot", "lock screen",
    "sleep display", "empty trash"
]


def detect_tool(user_input: str) -> str | None:
    text = user_input.lower()

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
    return None
