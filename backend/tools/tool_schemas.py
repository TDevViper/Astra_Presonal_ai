# ==========================================
# tools/tool_schemas.py
# JSON schemas for every ASTRA tool.
# The LLM reads these and decides which
# tool to call — no regex required.
# Compatible with Ollama's tool call format.
# ==========================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, prices, weather, or anything that needs live data. Use when the user asks about recent events or things you don't know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, concise and specific",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_monitor",
            "description": "Get real-time CPU usage, RAM usage, disk space, and top running processes. Use when the user asks about system performance, memory, or why their computer is slow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                        "enum": ["summary", "full"],
                        "description": "summary for quick stats, full for all processes",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_reader",
            "description": "Read a file from the local filesystem and return its contents. Use when the user asks to read, open, show, or analyze a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path to read, e.g. 'backend/main.py' or '~/Documents/notes.txt'",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_manager",
            "description": "Add, list, complete, or delete tasks and todos. Use when the user wants to manage their to-do list or reminders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "list", "complete", "delete"],
                        "description": "The action to perform",
                    },
                    "task": {
                        "type": "string",
                        "description": "The task title or description (required for add/complete/delete)",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git",
            "description": "Run git operations: status, log, branch info, or diff. Use when the user asks about git, commits, branches, or what changed in their code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["status", "log", "branch", "diff"],
                        "description": "The git operation to run",
                    }
                },
                "required": ["operation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python_sandbox",
            "description": "Execute a Python code snippet in a safe sandbox and return the output. Use when the user asks to run, execute, or test Python code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_controller",
            "description": "Control the computer: open or close apps, control music playback, adjust volume, take screenshots, or lock the screen. Use for any app control or system action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The natural language command, e.g. 'open Spotify', 'pause music', 'volume up', 'take screenshot'",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "smart_home",
            "description": "Control smart home devices: turn lights on/off, lock/unlock doors, adjust thermostat. Use when the user mentions lights, doors, or home automation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["turn_on", "turn_off", "lock", "unlock", "status"],
                        "description": "The action to perform",
                    },
                    "device": {
                        "type": "string",
                        "description": "The device or room name, e.g. 'bedroom light', 'front door'",
                    },
                },
                "required": ["action", "device"],
            },
        },
    },
]

# Quick lookup: tool name → schema
TOOL_SCHEMA_MAP = {s["function"]["name"]: s for s in TOOL_SCHEMAS}


def get_schemas_for_model(model: str) -> list:
    """
    Some older Ollama models don't support tool calling.
    Return schemas only for models that do.
    Tool-call capable models as of 2025: llama3.x, mistral, phi3.5+, qwen2+
    """
    TOOL_CAPABLE = {
        "llama3",
        "mistral",
        "qwen2",
        "phi3.5",
        "phi4",
        "command-r",
        "granite",
        "nemotron",
    }
    model_lower = model.lower()
    if any(cap in model_lower for cap in TOOL_CAPABLE):
        return TOOL_SCHEMAS
    return []  # fallback to regex routing for older models
