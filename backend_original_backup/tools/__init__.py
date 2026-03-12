from .tool_router import detect_tool, requires_approval
__all__ = ['detect_tool', 'requires_approval', 'dispatch_tool']

def dispatch_tool(tool_name: str, user_input: str, context: dict = {}) -> str:
    try:
        if tool_name == "web_search":
            from .web_search import handle_search_command
            return handle_search_command(user_input)
        elif tool_name == "tasks":
            from .task_manager import TaskManager
            from memory.memory_engine import load_memory
            return str(TaskManager(load_memory()).list_tasks())
        elif tool_name == "system_monitor":
            from .system_monitor import get_system_info
            return str(get_system_info())
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
        elif tool_name == "screen_watcher":
            from .screen_watcher import ScreenWatcher
            return ScreenWatcher().capture_and_analyze(user_input)
        elif tool_name == "smart_home":
            from .tool_router import route_tool
            return route_tool(user_input) or "Smart home command sent."
        elif tool_name == "device_discovery":
            from .device_discovery import DeviceDiscovery
            devices = DeviceDiscovery().scan_all()
            return f"Found {len(devices)} devices: {', '.join(list(devices.keys())[:10])}"
        elif tool_name == "whatsapp":
            from .whatsapp_tool import handle_whatsapp_command
            return handle_whatsapp_command(user_input)
        elif tool_name == "system":
            from .system_controller import handle_system_command
            return handle_system_command(user_input)
        elif tool_name == "files":
            from .file_reader import extract_filepath, read_file
            path = extract_filepath(user_input)
            return read_file(path) if path else "No file path found."
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Tool error ({tool_name}): {e}"
