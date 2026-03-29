import asyncio
# tools/shell_executor.py
# ASTRA shell executor with 3-tier safety model
# safe → elevated → root (each requires explicit confirmation)
import subprocess, logging, shlex, os
from typing import Dict

logger = logging.getLogger(__name__)

# Tier 1 — always allowed, no confirmation needed
SAFE_COMMANDS = {
    "ls", "pwd", "echo", "cat", "head", "tail", "grep", "find",
    "git", "python3", "pip", "which", "whoami", "date", "uptime",
    "df", "du", "ps", "top", "curl", "ping", "dig", "nslookup",
    "uname", "sw_vers", "system_profiler", "ollama", "redis-cli",
}

# Tier 2 — needs one confirmation
ELEVATED_COMMANDS = {
    "pip install", "pip uninstall", "brew install", "brew uninstall",
    "npm install", "npm uninstall", "rm ", "mv ", "cp ",
    "mkdir", "chmod", "chown", "kill", "pkill",
    "docker", "docker-compose", "systemctl", "launchctl",
}

# Tier 3 — needs explicit "I confirm sudo"
ROOT_COMMANDS = {"sudo", "su "}

BLOCKED = {"rm -rf /", "rm -rf ~", ":(){ :|:& };:", "mkfs", "dd if="}


# Shell metacharacters that enable chaining / injection
_SHELL_METACHAR = frozenset([';', '&&', '||', '`', '$(', '|'])

def _has_shell_injection(cmd: str) -> bool:
    for ch in _SHELL_METACHAR:
        if ch in cmd:
            return True
    return False

def classify_command(cmd: str) -> str:
    if _has_shell_injection(cmd):
        return "dangerous"  # piped/chained commands always elevated
    """Returns: safe | elevated | root | blocked"""
    c = cmd.strip().lower()
    if any(b in c for b in BLOCKED):
        return "blocked"
    if any(c.startswith(r) or f" {r}" in c for r in ROOT_COMMANDS):
        return "root"
    if any(c.startswith(e) or c.startswith(e.split()[0]) for e in ELEVATED_COMMANDS):
        return "elevated"
    first_word = c.split()[0] if c.split() else ""
    if first_word in SAFE_COMMANDS:
        return "safe"
    return "elevated"  # unknown → treat as elevated, require confirmation


def propose_shell(command: str) -> Dict:
    """Build a proposal dict — sent to frontend for approval."""
    tier = classify_command(command)
    if tier == "blocked":
        return {
            "approved":    False,
            "blocked":     True,
            "command":     command,
            "tier":        "blocked",
            "message":     "⛔ This command is permanently blocked for safety.",
        }
    warnings = {
        "safe":     "This command is read-only and safe to run.",
        "elevated": "⚠️ This command can modify files or install software. Review carefully.",
        "root":     "🔴 This requires sudo/root access. Type 'I confirm sudo' to proceed.",
    }
    return {
        "approved":         False,
        "blocked":          False,
        "command":          command,
        "tier":             tier,
        "message":          warnings[tier],
        "approval_required": tier != "safe",
    }


def execute_shell(command: str, confirmed: bool = False,
                  sudo_confirmed: bool = False) -> Dict:
    """
    Execute a shell command.
    - safe commands run immediately
    - elevated need confirmed=True
    - root need sudo_confirmed=True
    """
    tier = classify_command(command)

    if tier == "blocked":
        return {"success": False, "output": "⛔ Blocked command.", "tier": tier}

    if tier == "root" and not sudo_confirmed:
        return {"success": False,
                "output": "🔴 Root command requires explicit sudo confirmation.",
                "tier": tier, "needs_sudo_confirm": True}

    if tier == "elevated" and not confirmed:
        return {"success": False,
                "output": "⚠️ Elevated command requires confirmation.",
                "tier": tier, "needs_confirm": True}

    try:
        logger.info("shell_executor [%s]: %s", tier, command[:80])
        loop = asyncio.get_event_loop()
result = loop.run_in_executor(None, lambda: subprocess.run(
            shlex.split(command), shell=False, capture_output=True, text=True,
            timeout=30, cwd=os.path.expanduser("~")
        )
        output = result.stdout.strip() or result.stderr.strip() or "(no output)"
        return {
            "success":     result.returncode == 0,
            "output":      output[:3000],
            "returncode":  result.returncode,
            "tier":        tier,
            "command":     command,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "⏱ Command timed out (30s limit).", "tier": tier}
    except Exception as e:
        logger.error("shell_executor error: %s", e)
        return {"success": False, "output": f"Error: {e}", "tier": tier}
