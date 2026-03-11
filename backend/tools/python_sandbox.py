# tools/python_sandbox.py
# Sandboxed Python execution with hard resource limits
import subprocess, tempfile, os, logging, re
from typing import Dict

logger = logging.getLogger(__name__)

# Hard limits
_MAX_EXEC_SECONDS = 10
_MAX_OUTPUT_CHARS = 3000
_MAX_INPUT_CHARS  = 8000

_BLOCKED = [
    "import os", "import sys", "import subprocess", "import shutil",
    "__import__", "exec(", "eval(", "open(", "os.system", "os.popen",
    "socket", "requests", "urllib", "http", "ftplib", "smtplib",
    "importlib", "ctypes", "pickle", "marshal",
]


def extract_python_code(text: str) -> str:
    m = re.search(r'```python\s*(.*?)```', text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _is_safe(code: str) -> tuple[bool, str]:
    lower = code.lower()
    for pattern in _BLOCKED:
        if pattern in lower:
            return False, f"Blocked pattern: '{pattern}'"
    if len(code) > _MAX_INPUT_CHARS:
        return False, f"Code too long (max {_MAX_INPUT_CHARS} chars)"
    return True, ""


def propose_python_execution(code: str) -> Dict:
    safe, reason = _is_safe(code)
    if not safe:
        return {
            "success": False,
            "code": code,
            "output": f"Blocked: {reason}",
            "approved": False,
            "requires_approval": False,
        }
    return {
        "success": True,
        "code": code,
        "output": None,
        "approved": False,
        "requires_approval": True,
    }


def execute_python(code: str) -> Dict:
    safe, reason = _is_safe(code)
    if not safe:
        return {"success": False, "output": f"Blocked: {reason}", "error": reason}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                    delete=False, prefix='astra_sandbox_') as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python3", "-I", tmp_path],  # -I = isolated mode
            capture_output=True,
            text=True,
            timeout=_MAX_EXEC_SECONDS,
        )
        output = (result.stdout + result.stderr).strip()
        if len(output) > _MAX_OUTPUT_CHARS:
            output = output[:_MAX_OUTPUT_CHARS] + "\n... (truncated)"
        return {
            "success": result.returncode == 0,
            "output": output or "(no output)",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        logger.warning("Python sandbox timeout after %ds", _MAX_EXEC_SECONDS)
        return {"success": False, "output": f"Timed out after {_MAX_EXEC_SECONDS}s", "error": "timeout"}
    except Exception as e:
        logger.error("Python sandbox error: %s", e)
        return {"success": False, "output": str(e), "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
