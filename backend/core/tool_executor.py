# core/tool_executor.py
# Handles all tool dispatch logic, extracted from Brain._handle_tool_request
import logging, re
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ToolExecutor:

    def __init__(self, model_manager, build_reply_fn):
        self._mm           = model_manager
        self._build_reply  = build_reply_fn   # Brain._build_reply passed in

    def execute(self, tool: str, user_input: str, memory: Dict, user_name: str) -> Optional[Dict]:
        logger.info("tool | tool=%s", tool)
        handler = {
            "file_reader":    self._file_reader,
            "system_monitor": self._system_monitor,
            "task_manager":   self._task_manager,
            "git":            self._git,
            "python_sandbox": self._python_sandbox,
            "system_controller": self._system_controller,
            "face_recognition":  self._face_recognition,
        }.get(tool)
        if handler:
            return handler(user_input, memory, user_name)
        return None

    # ── File reader ───────────────────────────────────────────────────────

    def _file_reader(self, user_input: str, memory: Dict, user_name: str) -> Dict:
        from tools.file_reader import read_file, extract_filepath, list_files
        import ollama

        filepath = extract_filepath(user_input)
        if not filepath:
            if any(w in user_input.lower() for w in ["list", "show files", "what files"]):
                result = list_files()
                if result["success"]:
                    reply = (f"Files in {result['directory']}:\n" +
                             "\n".join(f"{'📁' if f['type']=='dir' else '📄'} {f['name']}"
                                      for f in result["files"][:20]))
                    if result["count"] > 20:
                        reply += f"\n... and {result['count'] - 20} more"
                else:
                    reply = f"Error: {result['error']}"
            else:
                reply = "Which file? Try: 'read backend.py'"
            return self._build_reply(reply, "neutral", "file_operation", "file_reader",
                                     tool_used=True, confidence=0.95)

        result = read_file(filepath)
        if result["success"]:
            prompt = (f"Analyze this file: 1 sentence description, 3-5 key components, "
                      f"any obvious issues. Under 100 words.\n\n"
                      f"File: {result['filepath']} ({result['lines']} lines)\n\n"
                      f"{result['content'][:3000]}")
            try:
                resp     = ollama.chat(
                    model=self._mm.select_model(user_input, "technical"),
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.3, "num_predict": 200}
                )
                analysis = resp["message"]["content"]
            except Exception as e:
                logger.warning("file analysis LLM failed: %s", e)
                analysis = f"Read {result['lines']} lines from {filepath}"
            reply = f"📄 {result['filepath']} ({result['lines']} lines)\n\n{analysis}"
            if result.get("truncated"):
                reply += f"\n\n(First {result['truncated_at']} lines shown)"
        else:
            reply = f"❌ {result['error']}"
        return self._build_reply(reply, "neutral", "file_analysis", "file_reader",
                                 tool_used=True, confidence=0.90)

    # ── System monitor ────────────────────────────────────────────────────

    def _system_monitor(self, user_input: str, memory: Dict, user_name: str) -> Dict:
        from tools.system_monitor import get_system_info, analyze_performance
        info = get_system_info()
        if "why" in user_input.lower() and "slow" in user_input.lower():
            summary = analyze_performance()
            reply   = f"System Status:\n{summary}\n\nTop Processes:\n"
            for p in info["top_processes"][:3]:
                reply += f"• {p['name']}: {p['cpu']}% CPU, {p['memory']}% RAM\n"
        elif info["success"]:
            reply = (f"💻 CPU: {info['cpu']['percent']}% | "
                     f"RAM: {info['memory']['used_gb']}/{info['memory']['total_gb']}GB | "
                     f"Disk: {info['disk']['free_gb']}GB free")
        else:
            reply = f"Error: {info['error']}"
        return self._build_reply(reply, "neutral", "system_info", "system_monitor",
                                 tool_used=True, confidence=0.95)

    # ── Task manager ──────────────────────────────────────────────────────

    def _task_manager(self, user_input: str, memory: Dict, user_name: str) -> Dict:
        from tools.task_manager import TaskManager
        tm, text = TaskManager(memory), user_input.lower()
        if any(w in text for w in ["add task", "new task", "remind me", "todo"]):
            m     = re.search(r'(?:add task|new task|remind me to|todo|task:)\s+(.+)',
                              user_input, re.IGNORECASE)
            reply = f"✓ {tm.add_task(m.group(1).strip())['message']}" if m else "What task?"
        elif any(w in text for w in ["my tasks", "show tasks", "list tasks"]):
            result = tm.list_tasks()
            if result["count"] == 0:
                reply = "No tasks! Want to add one?"
            else:
                reply = f"Tasks ({result['count']}):\n"
                for t in result["tasks"]:
                    emoji    = "✅" if t["status"] == "done" else "⏳"
                    priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t["priority"], "")
                    deadline = f" (due: {t['deadline']})" if t["deadline"] else ""
                    reply   += f"{emoji}{priority} {t['title']}{deadline}\n"
        elif any(w in text for w in ["complete", "done", "finish"]):
            result = tm.list_tasks(status="todo")
            if result["count"] > 0:
                task  = result["tasks"][0]
                tm.complete_task(task["id"])
                reply = f"✅ Completed: {task['title']}"
            else:
                reply = "No pending tasks!"
        else:
            reply = "Task commands: 'add task', 'my tasks', 'complete task'"
        return self._build_reply(reply, "neutral", "task_management", "task_manager",
                                 tool_used=True, confidence=0.95, memory_updated=True)

    # ── Git ───────────────────────────────────────────────────────────────

    def _git(self, user_input: str, memory: Dict, user_name: str) -> Dict:
        from tools.git_tool import is_git_repo, git_status, git_diff, git_log, git_branch, propose_git_commit
        if not is_git_repo():
            return self._build_reply("Not in a git repo.", "neutral", "git_error", "git", confidence=1.0)
        text = user_input.lower()
        if "status" in text or "what changed" in text:
            result = git_status()
            if result["success"]:
                if result.get("clean"):
                    reply = "Clean repo ✓"
                else:
                    reply = "Changes:\n"
                    if result.get("modified"):  reply += f"Modified: {', '.join(result['modified'])}\n"
                    if result.get("added"):     reply += f"Added: {', '.join(result['added'])}\n"
                    if result.get("untracked"): reply += f"Untracked: {', '.join(result['untracked'])}\n"
            else:
                reply = f"Error: {result['error']}"
        elif "log" in text or "commits" in text:
            result = git_log(5)
            reply  = ("Recent commits:\n" + "".join(
                f"• {c['hash']} {c['message']} ({c['time']})\n" for c in result.get("commits", []))
            ) if result["success"] else f"Error: {result['error']}"
        elif "branch" in text:
            result = git_branch()
            reply  = (f"Branch: {result['current_branch']}\n" + "".join(
                f"{'*' if b['current'] else ' '} {b['name']}\n" for b in result.get("branches", [])[:10])
            ) if result["success"] else f"Error: {result['error']}"
        elif "commit" in text:
            m        = re.search(r'commit\s+(.+?)$', user_input, re.IGNORECASE)
            proposal = propose_git_commit(m.group(1) if m else "Update files")
            if not proposal["success"]:
                reply = proposal["error"]
                return self._build_reply(reply, "neutral", "git_operation", "git",
                                         tool_used=True, confidence=0.90)
            return {"reply": "Git commit proposed", "emotion": "neutral",
                    "intent": "git_commit_proposal", "agent": "git",
                    "tool_used": True, "confidence": 1.0,
                    "approval_required": True, "proposal": proposal}
        elif "diff" in text:
            result = git_diff()
            reply  = (f"```\n{result['output'][:1000]}\n```"
                      + ("\n(truncated)" if len(result["output"]) > 1000 else "")
                     ) if result["success"] else f"Error: {result['error']}"
        else:
            reply = "Git: status | log | branch | commit | diff"
        return self._build_reply(reply, "neutral", "git_operation", "git",
                                 tool_used=True, confidence=0.90)

    # ── Python sandbox ────────────────────────────────────────────────────

    def _python_sandbox(self, user_input: str, memory: Dict, user_name: str) -> Dict:
        from tools.python_sandbox import propose_python_execution, extract_python_code
        code = extract_python_code(user_input)
        if not code:
            return self._build_reply("No Python code found. Wrap in ```python``` blocks.",
                                     "neutral", "python_error", "python_sandbox", confidence=0.80)
        return {"reply": "Python execution proposed", "emotion": "neutral",
                "intent": "python_execution_proposal", "agent": "python_sandbox",
                "tool_used": True, "confidence": 1.0,
                "approval_required": True, "proposal": propose_python_execution(code)}

    # ── System controller ─────────────────────────────────────────────────

    def _system_controller(self, user_input: str, memory: Dict, user_name: str) -> Dict:
        from tools.system_controller import handle_system_command
        try:
            result = handle_system_command(user_input)
            if result:
                return self._build_reply(result, "neutral", "system_control",
                                         "system_controller", tool_used=True, confidence=0.95)
        except Exception as e:
            logger.warning("system_controller failed: %s", e)
        return self._build_reply("I couldn't execute that system command.",
                                 "neutral", "system_control", "system_controller",
                                 tool_used=True, confidence=0.3)

    # ── Face recognition ──────────────────────────────────────────────────

    def _face_recognition(self, user_input: str, memory: Dict, user_name: str) -> Dict:
        import re
        from vision.face_recognition_engine import (
            identify_faces, learn_face, list_known_faces, forget_face
        )
        text = user_input.lower()

        # Learn: "remember this person as Priya" / "this is my friend John"
        learn_match = re.search(
            r'(?:remember|learn|this is|her name is|his name is|they are|name is)\s+(?:this person as |as |)([A-Za-z ]+)',
            user_input, re.IGNORECASE
        )
        if learn_match and any(w in text for w in ["remember", "learn", "this is", "name is"]):
            name = learn_match.group(1).strip().title()
            # Need image — signal that camera is needed
            return self._build_reply(
                f"Sure! Show me {name}'s face on camera and I'll remember them. "
                f"Use the camera button and say 'remember this as {name}'.",
                "neutral", "face_learn_pending", "face_recognition",
                tool_used=True, confidence=0.9
            )

        # List known faces
        if any(w in text for w in ["list", "who do you know", "known faces", "my faces"]):
            result = list_known_faces()
            return self._build_reply(result["message"], "neutral",
                                     "face_list", "face_recognition",
                                     tool_used=True, confidence=1.0)

        # Forget
        forget_match = re.search(r'forget\s+([A-Za-z ]+)', user_input, re.IGNORECASE)
        if forget_match:
            name   = forget_match.group(1).strip().title()
            result = forget_face(name)
            return self._build_reply(result["message"], "neutral",
                                     "face_forget", "face_recognition",
                                     tool_used=True, confidence=1.0)

        # Default — identify (needs camera image from frontend)
        return self._build_reply(
            "Point the camera at someone and I'll tell you who they are. "
            "Use the camera button and ask 'who is this?'",
            "neutral", "face_identify_pending", "face_recognition",
            tool_used=True, confidence=0.85
        )
