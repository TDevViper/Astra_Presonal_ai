"""Tests for shell_executor — tier classification and execution safety."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.shell_executor import classify_command, propose_shell, execute_shell


# ── Classification tests ──────────────────────────────────────

def test_safe_commands_classified_correctly():
    assert classify_command("ls") == "safe"
    assert classify_command("pwd") == "safe"
    assert classify_command("whoami") == "safe"
    assert classify_command("git status") == "safe"
    assert classify_command("python3 script.py") == "safe"


def test_elevated_commands_classified_correctly():
    assert classify_command("rm file.txt") == "elevated"
    assert classify_command("mv a b") == "elevated"
    assert classify_command("chmod 755 file") == "elevated"
    assert classify_command("pip install flask") == "elevated"
    assert classify_command("docker ps") == "elevated"


def test_root_commands_classified_correctly():
    assert classify_command("sudo apt install vim") == "root"
    assert classify_command("su root") == "root"


def test_blocked_commands_classified_correctly():
    assert classify_command("rm -rf /") == "blocked"
    assert classify_command("rm -rf ~") == "blocked"
    assert classify_command("mkfs /dev/sda") == "blocked"
    assert classify_command("dd if=/dev/zero of=/dev/sda") == "blocked"


def test_unknown_command_defaults_to_elevated():
    assert classify_command("somerandombinary --flag") == "elevated"


def test_classification_is_case_insensitive():
    assert classify_command("LS") == "safe"
    assert classify_command("RM file.txt") == "elevated"
    assert classify_command("SUDO reboot") == "root"


# ── Proposal tests ────────────────────────────────────────────

def test_propose_blocks_dangerous_command():
    result = propose_shell("rm -rf /")
    assert result["blocked"] is True
    assert result["approved"] is False


def test_propose_safe_command_no_approval_required():
    result = propose_shell("ls -la")
    assert result["approval_required"] is False
    assert result["tier"] == "safe"


def test_propose_elevated_requires_approval():
    result = propose_shell("rm file.txt")
    assert result["approval_required"] is True
    assert result["tier"] == "elevated"


def test_propose_root_requires_approval():
    result = propose_shell("sudo reboot")
    assert result["approval_required"] is True
    assert result["tier"] == "root"


# ── Execution tests ───────────────────────────────────────────

def test_blocked_command_never_executes():
    result = execute_shell("rm -rf /", confirmed=True, sudo_confirmed=True)
    assert result["success"] is False
    assert "Blocked" in result["output"] or "blocked" in result["output"].lower()


def test_elevated_without_confirmation_rejected():
    result = execute_shell("rm /tmp/fakefile", confirmed=False)
    assert result["success"] is False
    assert result.get("needs_confirm") is True


def test_root_without_sudo_confirmation_rejected():
    result = execute_shell("sudo ls", confirmed=True, sudo_confirmed=False)
    assert result["success"] is False
    assert result.get("needs_sudo_confirm") is True


def test_safe_command_executes_without_confirmation():
    result = execute_shell("echo hello")
    assert result["success"] is True
    assert "hello" in result["output"]


def test_safe_command_output_truncated_at_3000():
    result = execute_shell("python3 -c \"print('x' * 5000)\"")
    assert result["success"] is True
    assert len(result["output"]) <= 3000


def test_timeout_handled_gracefully(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired("cmd", 30)))
    result = execute_shell("echo hi")
    assert result["success"] is False
    assert "timed out" in result["output"].lower()
