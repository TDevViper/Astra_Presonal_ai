# ==========================================
# core/structured_tool_caller.py
# LLM-driven tool selection via Ollama's
# native tool/function calling API.
#
# Flow:
#   1. Send user message + tool schemas to LLM
#   2. LLM responds with tool_calls[] or plain text
#   3. Execute chosen tool with LLM-extracted args
#   4. Send tool result back to LLM for final reply
#   5. Return final natural language response
#
# Falls back to regex routing if model doesn't
# support tool calling or returns no tool call.
# ==========================================
import logging
import json
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StructuredToolCaller:
    def __init__(self, model_manager, tool_executor, build_reply_fn):
        self._mm = model_manager
        self._tools = tool_executor
        self._build_reply = build_reply_fn

    def try_tool_call(
        self,
        user_input: str,
        system_prompt: str,
        selected_model: str,
        history: List[Dict],
        memory: Dict,
        user_name: str,
    ) -> Optional[Dict]:
        """
        Attempt LLM-driven tool selection.
        Returns a Brain reply dict if a tool was used, else None.
        None means: fall through to normal LLM path.
        """
        from tools.tool_schemas import get_schemas_for_model

        schemas = get_schemas_for_model(selected_model)
        if not schemas:
            logger.debug(
                "Model %s doesn't support tool calling — skipping", selected_model
            )
            return None

        tool_call, args = self._ask_llm_for_tool(
            user_input, system_prompt, selected_model, history, schemas
        )

        if not tool_call:
            return None  # LLM chose not to use a tool

        logger.info("🔧 LLM selected tool: %s args=%s", tool_call, args)

        # Execute the tool
        tool_result = self._execute_tool(tool_call, args, user_input, memory, user_name)

        if tool_result is None:
            logger.warning("Tool %s returned None — falling back to LLM", tool_call)
            return None

        # Send result back to LLM for natural language synthesis
        final_reply = self._synthesize_reply(
            user_input, tool_call, tool_result, system_prompt, selected_model, history
        )

        reply = self._build_reply(
            final_reply,
            emotion="neutral",
            intent=f"tool_{tool_call}",
            agent=f"tool/{tool_call}",
            tool_used=True,
            confidence=0.92,
        )
        reply["tool_used"] = True
        return reply

    # ── Step 1: Ask the LLM which tool to use ─────────────────────────────

    def _ask_llm_for_tool(
        self,
        user_input: str,
        system_prompt: str,
        model: str,
        history: List[Dict],
        schemas: list,
    ) -> Tuple[Optional[str], Dict]:
        """
        Call Ollama with tools=[...].
        Returns (tool_name, arguments_dict) or (None, {}).
        """
        import ollama
        from config import config as _cfg

        messages = (
            [{"role": "system", "content": system_prompt}]
            + history[-6:]  # last 3 turns for context
            + [{"role": "user", "content": user_input}]
        )

        try:
            resp = ollama.Client(host=_cfg.OLLAMA_HOST).chat(
                model=model,
                messages=messages,
                tools=schemas,
                options={"temperature": 0.1, "num_predict": 256},
            )

            msg = resp.get("message", {})

            # Ollama returns tool_calls as a list on the message
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return None, {}

            # Take the first tool call
            first = tool_calls[0]
            fn = first.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})

            # Ollama sometimes returns args as a JSON string
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"query": args}

            return name, args

        except Exception as e:
            # Tool calling not supported by this Ollama version or model
            logger.debug("Tool call API failed (%s) — regex fallback will handle", e)
            return None, {}

    # ── Step 2: Execute the chosen tool ───────────────────────────────────

    def _execute_tool(
        self,
        tool_name: str,
        args: Dict,
        user_input: str,
        memory: Dict,
        user_name: str,
    ) -> Optional[str]:
        """Execute a tool and return a string result."""
        try:
            if tool_name == "web_search":
                return self._run_web_search(args.get("query", user_input))

            if tool_name == "system_monitor":
                from tools.system_monitor import get_system_info, analyze_performance

                info = get_system_info()
                if info.get("success"):
                    return (
                        f"CPU: {info['cpu']['percent']}% | "
                        f"RAM: {info['memory']['used_gb']}/{info['memory']['total_gb']}GB | "
                        f"Disk: {info['disk']['free_gb']}GB free\n"
                        f"Top process: {info['top_processes'][0]['name']} "
                        f"({info['top_processes'][0]['cpu']}% CPU)"
                        if info.get("top_processes")
                        else ""
                    )
                return f"System monitor error: {info.get('error')}"

            if tool_name == "file_reader":
                from tools.file_reader import read_file

                path = args.get("path", "")
                result = read_file(path)
                if result.get("success"):
                    return f"File: {result['filepath']} ({result['lines']} lines)\n\n{result['content'][:3000]}"
                return f"Error reading file: {result.get('error')}"

            if tool_name == "task_manager":
                from tools.task_manager import TaskManager

                tm = TaskManager(memory)
                action = args.get("action", "list")
                task = args.get("task", "")
                if action == "add" and task:
                    r = tm.add_task(task)
                    return r.get("message", f"Added task: {task}")
                elif action == "list":
                    r = tm.list_tasks()
                    if r["count"] == 0:
                        return "No tasks."
                    return "\n".join(
                        f"{'✅' if t['status'] == 'done' else '⏳'} {t['title']}"
                        for t in r["tasks"]
                    )
                elif action == "complete" and task:
                    r = tm.list_tasks(status="todo")
                    for t in r.get("tasks", []):
                        if task.lower() in t["title"].lower():
                            tm.complete_task(t["id"])
                            return f"Completed: {t['title']}"
                    return f"No pending task matching '{task}'"
                return "Task action done."

            if tool_name == "git":
                from tools.git_tool import (
                    git_status,
                    git_log,
                    git_branch,
                    git_diff,
                    is_git_repo,
                )

                if not is_git_repo():
                    return "Not in a git repository."
                op = args.get("operation", "status")
                if op == "status":
                    r = git_status()
                    if r.get("clean"):
                        return "Git repo is clean — no changes."
                    parts = []
                    if r.get("modified"):
                        parts.append(f"Modified: {', '.join(r['modified'])}")
                    if r.get("added"):
                        parts.append(f"Added: {', '.join(r['added'])}")
                    if r.get("untracked"):
                        parts.append(f"Untracked: {', '.join(r['untracked'])}")
                    return "\n".join(parts) or "No changes."
                elif op == "log":
                    r = git_log(5)
                    return "\n".join(
                        f"{c['hash']} — {c['message']} ({c['time']})"
                        for c in r.get("commits", [])
                    )
                elif op == "branch":
                    r = git_branch()
                    return f"Current branch: {r.get('current_branch')}"
                elif op == "diff":
                    r = git_diff()
                    return r.get("output", "")[:2000]

            if tool_name == "python_sandbox":
                from tools.python_sandbox import execute_python, _code_execution_allowed

                if not _code_execution_allowed():
                    return "Code execution is disabled. Set ALLOW_CODE_EXECUTION=true to enable."
                code = args.get("code", "")
                result = execute_python(code)
                return result.get("output", "No output.")

            if tool_name == "system_controller":
                from tools.system_controller import handle_system_command

                return handle_system_command(args.get("command", user_input))

            if tool_name == "smart_home":
                from tools.smart_home import SmartHome

                sh = SmartHome()
                action = args.get("action", "status")
                device = args.get("device", "light")
                if action == "turn_on":
                    sh.control_light(device, True)
                    return f"Turned on {device}."
                elif action == "turn_off":
                    sh.control_light(device, False)
                    return f"Turned off {device}."
                elif action == "lock":
                    sh.lock_door(device)
                    return f"Locked {device}."
                elif action == "unlock":
                    sh.unlock_door(device)
                    return f"Unlocked {device}."
                return f"Smart home: {device} status checked."

            logger.warning("No executor for tool: %s", tool_name)
            return None

        except Exception as e:
            logger.error("Tool execution error (%s): %s", tool_name, e)
            return f"Error running {tool_name}: {e}"

    def _run_web_search(self, query: str) -> str:
        try:
            from websearch.search import serper_search, format_results_for_llm

            results = serper_search(query, num_results=3)
            return format_results_for_llm(results) if results else "No results found."
        except Exception as e:
            logger.warning("Web search failed: %s", e)
            return f"Search error: {e}"

    # ── Step 3: Synthesize natural language reply from tool result ─────────

    def _synthesize_reply(
        self,
        user_input: str,
        tool_name: str,
        tool_result: str,
        system_prompt: str,
        model: str,
        history: List[Dict],
    ) -> str:
        """
        Send tool result back to the LLM to produce a natural response.
        This is the second LLM call — the 'tool result → answer' step.
        """
        import ollama
        from config import config as _cfg

        synthesis_prompt = (
            f"The user asked: {user_input}\n\n"
            f"You used the '{tool_name}' tool and got this result:\n"
            f"{tool_result}\n\n"
            f"Now give a clear, concise answer to the user based on this result. "
            f"Do not mention that you used a tool. Just answer naturally."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": synthesis_prompt},
        ]

        try:
            resp = ollama.Client(host=_cfg.OLLAMA_HOST).chat(
                model=model,
                messages=messages,
                options={"temperature": 0.4, "num_predict": 512},
            )
            return resp["message"]["content"].strip()
        except Exception as e:
            logger.error("Synthesis LLM call failed: %s", e)
            # If synthesis fails, return the raw tool result
            return tool_result
