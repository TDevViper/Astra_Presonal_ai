# ==========================================
# astra_engine/tools/git_tool.py
# ==========================================

import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional

import logging
logger = logging.getLogger(__name__)

# Git commands that are safe (read-only)
SAFE_COMMANDS = ["status", "diff", "log", "branch", "show", "ls-files"]

# Git commands that need approval
APPROVAL_COMMANDS = ["add", "commit", "push", "pull", "checkout", "merge", "rebase"]


def get_git_root() -> Optional[str]:
    """Find git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


def is_git_repo() -> bool:
    """Check if current directory is in a git repo."""
    return get_git_root() is not None


def run_git_command(command: List[str], cwd: str = None) -> Dict:
    """
    Execute git command safely.
    Returns: {"success": bool, "output": str, "error": str}
    """
    try:
        if not cwd:
            cwd = get_git_root() or os.getcwd()

        result = subprocess.run(
            ["git"] + command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def git_status() -> Dict:
    """Get git status."""
    result = run_git_command(["status", "--short"])
    if result["success"]:
        lines = result["output"].split("\n") if result["output"] else []
        
        modified = [l[3:] for l in lines if l.startswith(" M")]
        added = [l[3:] for l in lines if l.startswith("A ")]
        deleted = [l[3:] for l in lines if l.startswith(" D")]
        untracked = [l[3:] for l in lines if l.startswith("??")]

        return {
            "success": True,
            "modified": modified,
            "added": added,
            "deleted": deleted,
            "untracked": untracked,
            "clean": len(lines) == 0
        }
    return result


def git_diff(file: str = None) -> Dict:
    """Get git diff."""
    cmd = ["diff"]
    if file:
        cmd.append(file)
    return run_git_command(cmd)


def git_log(count: int = 5) -> Dict:
    """Get recent commits."""
    result = run_git_command([
        "log",
        f"-{count}",
        "--pretty=format:%h|%an|%ar|%s"
    ])
    
    if result["success"]:
        commits = []
        for line in result["output"].split("\n"):
            if line:
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "time": parts[2],
                        "message": parts[3]
                    })
        result["commits"] = commits
    
    return result


def git_branch() -> Dict:
    """List branches."""
    result = run_git_command(["branch", "-a"])
    if result["success"]:
        branches = []
        current = None
        for line in result["output"].split("\n"):
            if line.startswith("*"):
                current = line[2:].strip()
                branches.append({"name": current, "current": True})
            elif line.strip():
                branches.append({"name": line.strip(), "current": False})
        result["branches"] = branches
        result["current_branch"] = current
    return result


def propose_git_commit(message: str, files: List[str] = None) -> Dict:
    """
    Propose a git commit (doesn't execute).
    Returns proposal for frontend approval.
    """
    status = git_status()
    
    if not status["success"]:
        return {"success": False, "error": "Not a git repository"}
    
    if status["clean"]:
        return {"success": False, "error": "No changes to commit"}

    # Get diff preview
    diff_result = git_diff()
    
    return {
        "success": True,
        "type": "approval_required",
        "tool": "git",
        "action": "commit",
        "params": {
            "message": message,
            "files": files or ["--all"]
        },
        "preview": {
            "modified": len(status["modified"]),
            "added": len(status["added"]),
            "deleted": len(status["deleted"]),
            "files": status["modified"] + status["added"] + status["deleted"],
            "diff_snippet": diff_result["output"][:500] if diff_result["success"] else None
        }
    }


def execute_git_commit(message: str, files: List[str] = None) -> Dict:
    """
    Execute git commit (after approval).
    """
    # Add files
    if files and files != ["--all"]:
        for f in files:
            result = run_git_command(["add", f])
            if not result["success"]:
                return result
    else:
        result = run_git_command(["add", "--all"])
        if not result["success"]:
            return result

    # Commit
    return run_git_command(["commit", "-m", message])