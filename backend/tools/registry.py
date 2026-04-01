import importlib
# tools/registry.py — Plugin registry for ReAct tools
# Usage:
#   from tools.registry import tool
#
#   @tool("rag_search", "search ingested documents for relevant context")
#   def rag_search(query: str) -> str:
#       ...
#
# Any file in tools/ that uses @tool is auto-loaded on first import of this module.

import os
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, dict] = {}  # name → {fn, description}


def tool(name: str, description: str = ""):
    """Decorator that registers a function as a ReAct tool."""

    def decorator(fn: Callable):
        _REGISTRY[name.lower()] = {"fn": fn, "description": description}
        logger.debug(f"Tool registered: {name}")
        return fn

    return decorator


def execute(tool_name: str, arg: str, user_name: str = "User") -> str | None:
    """
    Try to execute tool_name from the registry.
    Returns None if tool not found (so caller can fall back to hardcoded tools).
    """
    entry = _REGISTRY.get(tool_name.lower())
    if not entry:
        return None
    try:
        result = entry["fn"](arg)
        return str(result) if result is not None else "(no output)"
    except Exception as e:
        return f"Tool error ({tool_name}): {e}"


def descriptions() -> str:
    """Return tool descriptions formatted for injection into ReAct system prompt."""
    if not _REGISTRY:
        return ""
    lines = []
    for name, entry in _REGISTRY.items():
        desc = entry.get("description", "")
        lines.append(f"- {name}(argument)      {desc}")
    return "\n".join(lines)


def list_tools() -> list[str]:
    return list(_REGISTRY.keys())


def _autoload():
    """Auto-import all tools/*.py files so @tool decorators self-register."""
    tools_dir = os.path.dirname(__file__)
    for fname in sorted(os.listdir(tools_dir)):
        if fname.startswith("_") or not fname.endswith(".py"):
            continue
        if fname in ("registry.py", "tool_router.py"):
            continue
        module_name = f"tools.{fname[:-3]}"
        try:
            importlib.import_module(module_name)
        except Exception as e:
            logger.debug(f"Autoload skipped {fname}: {e}")

    # Load plugins/
    import sys
    import importlib.util as _ilib_util

    plugins_dir = os.path.join(os.path.dirname(tools_dir), "plugins")
    if os.path.isdir(plugins_dir):
        for fname in sorted(os.listdir(plugins_dir)):
            if fname.startswith("_") or not fname.endswith(".py"):
                continue
            fpath = os.path.join(plugins_dir, fname)
            mod_name = f"plugins.{fname[:-3]}"
            try:
                if mod_name not in sys.modules:
                    spec = _ilib_util.spec_from_file_location(mod_name, fpath)
                    mod = _ilib_util.module_from_spec(spec)
                    sys.modules[mod_name] = mod
                    spec.loader.exec_module(mod)
                    logger.info(f"Plugin loaded: {fname}")
            except Exception as e:
                logger.debug(f"Plugin skipped {fname}: {e}")


_autoload()
