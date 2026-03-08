from .tool_router import detect_tool, requires_approval

__all__ = ['detect_tool', 'requires_approval', 'dispatch_tool']


def dispatch_tool(tool_name: str, user_input: str, context: dict) -> str:
    try:
        if tool_name == "web_search":
            from .web_search import handle_search_command
            return handle_search_command(user_input)
        elif tool_name == "tasks":
            from .task_manager import TaskManager
            from memory.memory_engine import load_memory
            return str(TaskManager(load_memory()).list_tasks())
        elif tool_name == "system_monitor":
            from .system_monitor import get_system_stats
            return str(get_system_stats())
        elif tool_name == "calendar":
            from .calendar_tool import handle_calendar_command
            return handle_calendar_command(user_input)
        elif tool_name == "git":
            from .git_tool import git_status
            return git_status().get("output", "No git info")
        elif tool_name == "python_sandbox":
            from .python_sandbox import propose_python_execution, extract_python_code
            code = extract_python_code(user_input)
            return str(propose_python_execution(code)) if code else "No code found"
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Tool error: {e}"
