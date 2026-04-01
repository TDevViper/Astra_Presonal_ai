"""
True container-level Python sandbox.
Replaces AST-walking python_sandbox.py with Docker isolation.
- No network access
- No filesystem access (tmpfs only)
- 10 second hard timeout
- 128MB memory cap
- Runs as unprivileged user
- Container auto-deleted after run
"""

import subprocess
import tempfile
import os
import logging
import json

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "astra-sandbox:latest"
TIMEOUT_SECONDS = 10
MEMORY_LIMIT = "128m"
CPU_LIMIT = "0.5"


def _is_docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
        return True
    except Exception:
        return False


def run_python(code: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """
    Run Python code in an isolated Docker container.
    Returns {"stdout": str, "stderr": str, "exit_code": int, "error": str|None}
    """
    if not _is_docker_available():
        logger.warning("Docker not available — falling back to AST sandbox")
        from tools.python_sandbox import run_code as legacy_run

        result = legacy_run(code)
        return {
            "stdout": result.get("output", ""),
            "stderr": "",
            "exit_code": 0,
            "error": result.get("error"),
        }

    # Write code to a temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        script_path = f.name

    try:
        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            MEMORY_LIMIT,
            "--cpus",
            CPU_LIMIT,
            "--read-only",
            "--tmpfs",
            "/tmp:size=32m,noexec",
            "--tmpfs",
            "/code:size=8m",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--cap-drop",
            "ALL",
            "-v",
            f"{script_path}:/code/script.py:ro",
            SANDBOX_IMAGE,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2,  # docker overhead buffer
        )

        return {
            "stdout": result.stdout[:8000],  # cap output size
            "stderr": result.stderr[:2000],
            "exit_code": result.returncode,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        # Kill the container if it's still running
        subprocess.run(
            ["docker", "kill", "--signal=SIGKILL"] + [f"astra-sandbox-{os.getpid()}"],
            capture_output=True,
        )
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": f"Execution timed out after {timeout}s",
        }

    except Exception as e:
        logger.error("Docker sandbox error: %s", e)
        return {"stdout": "", "stderr": "", "exit_code": -1, "error": str(e)}

    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


def run_python_with_result(code: str) -> str:
    """
    Convenience wrapper — returns a human-readable string for ASTRA replies.
    """
    result = run_python(code)
    if result["error"]:
        return f"❌ Sandbox error: {result['error']}"
    if result["exit_code"] != 0:
        return f"❌ Exit code {result['exit_code']}:\n{result['stderr'] or result['stdout']}"
    return result["stdout"] or "✅ Code ran successfully (no output)"
