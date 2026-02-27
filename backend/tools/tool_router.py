from .file_reader import read_file
from .api_caller import call_api

TOOLS = ["file_reader", "system_monitor", "task_manager", "git", "python_sandbox"]

APPROVAL_REQUIRED = ["git", "python_sandbox"]

FILE_TRIGGERS = ["read ", "open ", "show file", "read file", "cat ", "view file"]
SYSTEM_TRIGGERS = ["cpu", "memory", "ram", "disk", "system", "how slow", "why slow", "performance", "processes"]
TASK_TRIGGERS = ["add task", "new task", "my tasks", "show tasks", "list tasks", "remind me", "todo", "complete task", "finish task"]
GIT_TRIGGERS = ["git status", "git log", "git commit", "git branch", "git diff", "what changed", "commit ", "show commits"]
PYTHON_TRIGGERS = ["```python", "run python", "execute python", "run this code", "run code"]


def detect_tool(user_input: str) -> str | None:
    text = user_input.lower()

    if any(t in text for t in PYTHON_TRIGGERS):
        return "python_sandbox"

    if any(t in text for t in GIT_TRIGGERS):
        return "git"

    if any(t in text for t in TASK_TRIGGERS):
        return "task_manager"

    if any(t in text for t in SYSTEM_TRIGGERS):
        return "system_monitor"

    if any(t in text for t in FILE_TRIGGERS):
        return "file_reader"

    return None


def requires_approval(tool: str) -> bool:
    return tool in APPROVAL_REQUIRED


def route_tool(user_text: str):
    """Legacy route_tool kept for backwards compatibility."""
    text = user_text.lower()

    if text.startswith("read "):
        path = user_text.replace("read ", "").strip()
        return read_file(path)

    if text.startswith("api "):
        url = user_text.replace("api ", "").strip()
        return call_api(url)

    return None
