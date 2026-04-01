# tools/chain_planner.py
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

logger = logging.getLogger(__name__)

CHAIN_KEYWORDS = {
    "search": ["search", "find", "look up", "google", "what is", "latest"],
    "save_file": ["save", "write to file", "store", "export"],
    "summarize": ["summarize", "summary", "tldr", "brief"],
    "remind": ["remind", "reminder", "alert me"],
    "add_task": ["add task", "create task", "todo"],
    "run_code": ["run", "execute", "python"],
    "git": ["git status", "git log", "what changed", "commits"],
    "system": ["cpu", "ram", "memory usage", "disk space"],
}

CHAIN_CONNECTORS = ["and then", "and also", "then", "after that", "also", "next", "and"]

# Tools that can run in parallel (no data dependency on each other)
PARALLEL_SAFE = {"search", "git", "system", "remind"}


def detect_chain(user_input: str) -> list:
    text = user_input.lower()
    has_connector = any(f" {c} " in f" {text} " for c in CHAIN_CONNECTORS)
    if not has_connector:
        return []
    steps = []
    for tool, keywords in CHAIN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            steps.append(tool)
    return steps if len(steps) > 1 else []


def build_chain_plan(user_input: str, detected_steps: list) -> list:
    text = user_input.lower()
    plan = []
    for step in detected_steps:
        if step == "search":
            query = user_input
            for connector in CHAIN_CONNECTORS:
                if connector in text:
                    query = user_input[: text.index(connector)].strip()
                    break
            plan.append({"tool": "search", "input": query, "parallel": True})
        elif step == "save_file":
            path_match = re.search(
                r'(?:to|as|named?)\s+["\']?([^\s"\']+\.?\w+)["\']?', text
            )
            path = path_match.group(1) if path_match else "astra_output.txt"
            if "." not in path:
                path += ".txt"
            plan.append(
                {
                    "tool": "save_file",
                    "path": path,
                    "input": "__prev__",
                    "parallel": False,
                }
            )
        elif step == "summarize":
            plan.append({"tool": "summarize", "input": "__prev__", "parallel": False})
        elif step == "remind":
            plan.append({"tool": "remind", "input": user_input, "parallel": True})
        elif step == "add_task":
            plan.append({"tool": "add_task", "input": user_input, "parallel": True})
        elif step == "git":
            plan.append({"tool": "git", "input": user_input, "parallel": True})
        elif step == "system":
            plan.append({"tool": "system", "input": user_input, "parallel": True})
    return plan


def _run_step(step: Dict, prev_result: str) -> str:
    """Execute a single chain step. Returns result string."""
    inp = prev_result if step.get("input") == "__prev__" else step.get("input", "")
    tool = step["tool"]
    try:
        if tool == "search":
            from websearch.search_agent import WebSearchAgent

            result = WebSearchAgent().run(inp)
            return result.get("reply", "No results.")

        elif tool == "save_file":
            path = step.get("path", "astra_output.txt")
            with open(path, "w") as f:
                f.write(prev_result)
            return f"Saved to {path}"

        elif tool == "summarize":
            words = inp.split()
            return " ".join(words[:80]) + ("..." if len(words) > 80 else "")

        elif tool == "remind":
            return f"Reminder set: {inp}"

        elif tool == "add_task":
            return f"Task added: {inp}"

        elif tool == "git":
            from tools.git_tool import is_git_repo, git_status, git_log

            if not is_git_repo():
                return "Not in a git repo."
            if "log" in inp.lower() or "commits" in inp.lower():
                r = git_log(3)
                return (
                    (
                        "Recent commits:\n"
                        + "".join(
                            f"• {c['hash']} {c['message']}\n"
                            for c in r.get("commits", [])
                        )
                    )
                    if r["success"]
                    else r["error"]
                )
            r = git_status()
            if not r["success"]:
                return r["error"]
            if r.get("clean"):
                return "Git: clean working tree."
            modified = r.get("modified", [])
            return f"Git: {len(modified)} modified file(s): {', '.join(modified[:5])}"

        elif tool == "system":
            from tools.system_monitor import get_system_info

            info = get_system_info()
            if info["success"]:
                return (
                    f"CPU: {info['cpu']['percent']}% | "
                    f"RAM: {info['memory']['used_gb']}/{info['memory']['total_gb']}GB | "
                    f"Disk: {info['disk']['free_gb']}GB free"
                )
            return f"System error: {info['error']}"

    except Exception as e:
        logger.warning("chain step %s failed: %s", tool, e)
        return f"[{tool}] error: {e}"

    return f"[{tool}] no handler"


def execute_chain(plan: list, brain=None) -> str:
    """
    Execute chain plan. Parallel-safe steps run concurrently via ThreadPoolExecutor.
    Steps with input='__prev__' run sequentially after their dependency.
    """
    if not plan:
        return ""

    results: Dict[str, str] = {}
    ordered_output: List[str] = []
    prev_result = ""

    # Split into parallel batch (first run) and sequential steps
    parallel_steps = [
        s for s in plan if s.get("parallel") and s.get("input") != "__prev__"
    ]
    sequential_steps = [
        s for s in plan if not s.get("parallel") or s.get("input") == "__prev__"
    ]

    # Run parallel steps concurrently
    if parallel_steps:
        with ThreadPoolExecutor(max_workers=min(4, len(parallel_steps))) as ex:
            future_to_step = {ex.submit(_run_step, s, ""): s for s in parallel_steps}
            for future in as_completed(future_to_step):
                step = future_to_step[future]
                result = future.result()
                results[step["tool"]] = result
                ordered_output.append(f"[{step['tool'].upper()}] {result}")
                prev_result = result  # last parallel result becomes prev for sequential

    # Run sequential steps in order
    for step in sequential_steps:
        result = _run_step(step, prev_result)
        results[step["tool"]] = result
        ordered_output.append(f"[{step['tool'].upper()}] {result}")
        prev_result = result

    return "\n".join(ordered_output)
