# ==========================================
# tests/test_tool_executor.py
# ==========================================
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch, MagicMock


def _make_executor():
    from core.tool_executor import ToolExecutor
    mm = MagicMock()
    mm.select_model.return_value = "phi3:mini"

    def _build_reply(reply, emotion, intent, agent,
                     tool_used=False, memory_updated=False,
                     citations=None, results_count=0, confidence=0.6):
        return {"reply": reply, "emotion": emotion, "intent": intent,
                "agent": agent, "tool_used": tool_used,
                "memory_updated": memory_updated, "confidence": confidence,
                "confidence_label": "HIGH", "confidence_emoji": "🟢"}

    return ToolExecutor(mm, _build_reply)


MEM  = {"preferences": {"name": "Arnav"}, "tasks": []}
USER = "Arnav"


# ── execute() dispatch ─────────────────────────────────────────────────────

class TestDispatch(unittest.TestCase):

    def test_unknown_tool_returns_none(self):
        ex = _make_executor()
        self.assertIsNone(ex.execute("nonexistent_tool", "hi", MEM, USER))

    def test_known_tool_dispatched(self):
        ex = _make_executor()
        with patch.object(ex, "_system_monitor", return_value={"reply": "ok"}) as mock:
            result = ex.execute("system_monitor", "cpu usage", MEM, USER)
        mock.assert_called_once()
        self.assertEqual(result["reply"], "ok")

    def test_all_tool_names_resolve(self):
        ex = _make_executor()
        tools = ["file_reader", "system_monitor", "task_manager",
                 "git", "python_sandbox", "system_controller", "face_recognition"]
        for tool in tools:
            handler = {
                "file_reader":       ex._file_reader,
                "system_monitor":    ex._system_monitor,
                "task_manager":      ex._task_manager,
                "git":               ex._git,
                "python_sandbox":    ex._python_sandbox,
                "system_controller": ex._system_controller,
                "face_recognition":  ex._face_recognition,
            }.get(tool)
            self.assertIsNotNone(handler, f"{tool} missing from dispatch table")


# ── System monitor ─────────────────────────────────────────────────────────

class TestSystemMonitor(unittest.TestCase):

    def _fake_info(self):
        return {
            "success": True,
            "cpu": {"percent": 42},
            "memory": {"used_gb": 4, "total_gb": 16},
            "disk": {"free_gb": 100},
            "top_processes": [{"name": "ollama", "cpu": 80, "memory": 10}]
        }

    def test_returns_cpu_ram_disk(self):
        ex = _make_executor()
        with patch("tools.system_monitor.get_system_info", return_value=self._fake_info()), \
             patch("tools.system_monitor.analyze_performance", return_value="slow"):
            result = ex._system_monitor("cpu", MEM, USER)
        self.assertIn("CPU", result["reply"])
        self.assertIn("42", result["reply"])
        self.assertTrue(result["tool_used"])

    def test_slow_query_triggers_analysis(self):
        ex = _make_executor()
        with patch("tools.system_monitor.get_system_info", return_value=self._fake_info()), \
             patch("tools.system_monitor.analyze_performance", return_value="Memory pressure") as mock_perf:
            result = ex._system_monitor("why is it so slow", MEM, USER)
        mock_perf.assert_called_once()
        self.assertIn("reply", result)

    def test_error_info_returns_error_reply(self):
        ex = _make_executor()
        with patch("tools.system_monitor.get_system_info",
                   return_value={"success": False, "error": "psutil failed"}), \
             patch("tools.system_monitor.analyze_performance", return_value=""):
            result = ex._system_monitor("cpu", MEM, USER)
        self.assertIn("Error", result["reply"])


# ── Task manager ───────────────────────────────────────────────────────────

class TestTaskManager(unittest.TestCase):

    def _mock_tm(self):
        tm = MagicMock()
        tm.add_task.return_value      = {"message": "Task added: buy milk"}
        tm.list_tasks.return_value    = {
            "count": 2,
            "tasks": [
                {"title": "buy milk", "status": "todo", "priority": "high", "deadline": None, "id": "1"},
                {"title": "call doctor", "status": "todo", "priority": "low", "deadline": "2025-01-01", "id": "2"},
            ]
        }
        tm.complete_task.return_value = {"message": "done"}
        return tm

    def test_add_task(self):
        ex = _make_executor()
        with patch("tools.task_manager.TaskManager", return_value=self._mock_tm()):
            result = ex._task_manager("add task buy milk", MEM, USER)
        self.assertIn("buy milk", result["reply"])
        self.assertTrue(result["tool_used"])

    def test_list_tasks(self):
        ex = _make_executor()
        with patch("tools.task_manager.TaskManager", return_value=self._mock_tm()):
            result = ex._task_manager("show my tasks", MEM, USER)
        self.assertIn("buy milk", result["reply"])

    def test_list_tasks_empty(self):
        ex = _make_executor()
        tm = self._mock_tm()
        tm.list_tasks.return_value = {"count": 0, "tasks": []}
        with patch("tools.task_manager.TaskManager", return_value=tm):
            result = ex._task_manager("list tasks", MEM, USER)
        self.assertIn("No tasks", result["reply"])

    def test_complete_task(self):
        ex = _make_executor()
        with patch("tools.task_manager.TaskManager", return_value=self._mock_tm()):
            result = ex._task_manager("complete task", MEM, USER)
        self.assertIn("buy milk", result["reply"])

    def test_complete_task_none_pending(self):
        ex = _make_executor()
        tm = self._mock_tm()
        tm.list_tasks.return_value = {"count": 0, "tasks": []}
        with patch("tools.task_manager.TaskManager", return_value=tm):
            result = ex._task_manager("done with task", MEM, USER)
        self.assertIn("No pending", result["reply"])

    def test_unknown_task_command(self):
        ex = _make_executor()
        with patch("tools.task_manager.TaskManager", return_value=self._mock_tm()):
            result = ex._task_manager("something random", MEM, USER)
        self.assertIn("Task commands", result["reply"])


# ── Git ────────────────────────────────────────────────────────────────────

class TestGit(unittest.TestCase):

    def test_not_git_repo(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=False):
            result = ex._git("git status", MEM, USER)
        self.assertIn("Not in a git repo", result["reply"])

    def test_git_status_clean(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=True), \
             patch("tools.git_tool.git_status",
                   return_value={"success": True, "clean": True}):
            result = ex._git("git status", MEM, USER)
        self.assertIn("Clean", result["reply"])

    def test_git_status_with_changes(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=True), \
             patch("tools.git_tool.git_status",
                   return_value={"success": True, "clean": False,
                                 "modified": ["brain.py"], "added": [], "untracked": []}):
            result = ex._git("what changed", MEM, USER)
        self.assertIn("brain.py", result["reply"])

    def test_git_log(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=True), \
             patch("tools.git_tool.git_log",
                   return_value={"success": True,
                                 "commits": [{"hash": "abc123", "message": "init", "time": "1h ago"}]}):
            result = ex._git("show git log", MEM, USER)
        self.assertIn("abc123", result["reply"])

    def test_git_branch(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=True), \
             patch("tools.git_tool.git_branch",
                   return_value={"success": True, "current_branch": "main",
                                 "branches": [{"name": "main", "current": True}]}):
            result = ex._git("git branch", MEM, USER)
        self.assertIn("main", result["reply"])

    def test_git_diff(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=True), \
             patch("tools.git_tool.git_diff",
                   return_value={"success": True, "output": "+new line\n-old line"}):
            result = ex._git("git diff", MEM, USER)
        self.assertIn("new line", result["reply"])

    def test_git_commit_proposal(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=True), \
             patch("tools.git_tool.propose_git_commit",
                   return_value={"success": True, "proposal": "feat: update brain"}):
            result = ex._git("commit my changes", MEM, USER)
        self.assertTrue(result.get("approval_required"))

    def test_git_unknown_command(self):
        ex = _make_executor()
        with patch("tools.git_tool.is_git_repo", return_value=True):
            result = ex._git("do something git", MEM, USER)
        self.assertIn("Git:", result["reply"])


# ── Python sandbox ─────────────────────────────────────────────────────────

class TestPythonSandbox(unittest.TestCase):

    def test_no_code_returns_error(self):
        ex = _make_executor()
        with patch("tools.python_sandbox.extract_python_code", return_value=None):
            result = ex._python_sandbox("run some python", MEM, USER)
        self.assertIn("No Python code", result["reply"])

    def test_code_found_returns_proposal(self):
        ex = _make_executor()
        with patch("tools.python_sandbox.extract_python_code", return_value="print('hi')"), \
             patch("tools.python_sandbox.propose_python_execution",
                   return_value={"code": "print('hi')", "safe": True}):
            result = ex._python_sandbox("run ```python\nprint('hi')\n```", MEM, USER)
        self.assertTrue(result.get("approval_required"))
        self.assertEqual(result["intent"], "python_execution_proposal")


# ── System controller ──────────────────────────────────────────────────────

class TestSystemController(unittest.TestCase):

    def test_successful_command(self):
        ex = _make_executor()
        with patch("tools.system_controller.handle_system_command",
                   return_value="Volume set to 50%"):
            result = ex._system_controller("set volume to 50", MEM, USER)
        self.assertIn("Volume", result["reply"])
        self.assertTrue(result["tool_used"])

    def test_none_result_returns_fallback(self):
        ex = _make_executor()
        with patch("tools.system_controller.handle_system_command", return_value=None):
            result = ex._system_controller("do something", MEM, USER)
        self.assertIn("couldn't execute", result["reply"])

    def test_exception_returns_fallback(self):
        ex = _make_executor()
        with patch("tools.system_controller.handle_system_command",
                   side_effect=Exception("permission denied")):
            result = ex._system_controller("lock screen", MEM, USER)
        self.assertIn("couldn't execute", result["reply"])


# ── Face recognition ───────────────────────────────────────────────────────

class TestFaceRecognition(unittest.TestCase):

    def test_learn_face_returns_pending(self):
        ex = _make_executor()
        result = ex._face_recognition("remember this person as Priya", MEM, USER)
        self.assertIn("Priya", result["reply"])
        self.assertEqual(result["intent"], "face_learn_pending")

    def test_list_faces(self):
        ex = _make_executor()
        with patch("vision.face_recognition_engine.list_known_faces",
                   return_value={"message": "Known: Arnav, Priya"}):
            result = ex._face_recognition("list known faces", MEM, USER)
        self.assertIn("Known", result["reply"])

    def test_forget_face(self):
        ex = _make_executor()
        with patch("vision.face_recognition_engine.forget_face",
                   return_value={"message": "Forgot Priya"}):
            result = ex._face_recognition("forget Priya", MEM, USER)
        self.assertIn("Forgot", result["reply"])

    def test_default_identify(self):
        ex = _make_executor()
        result = ex._face_recognition("who is this person", MEM, USER)
        self.assertIn("camera", result["reply"].lower())


# ── File reader ────────────────────────────────────────────────────────────

class TestFileReader(unittest.TestCase):

    def test_no_filepath_asks_which_file(self):
        ex = _make_executor()
        with patch("tools.file_reader.extract_filepath", return_value=None), \
             patch("tools.file_reader.list_files", return_value={"success": True, "directory": "/", "files": [], "count": 0}):
            result = ex._file_reader("read something", MEM, USER)
        self.assertIn("Which file", result["reply"])

    def test_list_files(self):
        ex = _make_executor()
        with patch("tools.file_reader.extract_filepath", return_value=None), \
             patch("tools.file_reader.list_files", return_value={
                 "success": True, "directory": "/home",
                 "files": [{"name": "brain.py", "type": "file"}], "count": 1}):
            result = ex._file_reader("list files", MEM, USER)
        self.assertIn("brain.py", result["reply"])

    def test_read_file_success(self):
        ex = _make_executor()
        with patch("tools.file_reader.extract_filepath", return_value="brain.py"), \
             patch("tools.file_reader.read_file", return_value={
                 "success": True, "filepath": "brain.py",
                 "lines": 100, "content": "import os", "truncated": False}), \
             patch("ollama.chat", return_value={"message": {"content": "Main brain module."}}):
            result = ex._file_reader("read brain.py", MEM, USER)
        self.assertIn("brain.py", result["reply"])
        self.assertTrue(result["tool_used"])

    def test_read_file_error(self):
        ex = _make_executor()
        with patch("tools.file_reader.extract_filepath", return_value="missing.py"), \
             patch("tools.file_reader.read_file",
                   return_value={"success": False, "error": "File not found"}):
            result = ex._file_reader("read missing.py", MEM, USER)
        self.assertIn("File not found", result["reply"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
