# ==========================================
# tools/python_sandbox.py
# Safe execution — subprocess + timeout + blocklist
# ==========================================

import subprocess
import tempfile
import os
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

MAX_EXECUTION_TIME = 5
MAX_OUTPUT_SIZE    = 5000

# Hard blocked — never execute these
BLOCKED_PATTERNS = [
    r"os\.system",
    r"os\.popen",
    r"os\.remove",
    r"os\.rmdir",
    r"shutil\.rmtree",
    r"subprocess\.",
    r"__import__",
    r"eval\s*\(",
    r"exec\s*\(",
    r"open\s*\(",
    r"importlib",
    r"socket\.",
    r"requests\.",
    r"urllib",
    r"rm\s+-rf",
    r"sys\.exit",
]


def _is_safe(code: str) -> tuple[bool, list]:
    """Check code for dangerous patterns. Returns (is_safe, warnings)."""
    warnings = []
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            warnings.append(pattern.replace("\\", "").replace("s*", ""))
    return len(warnings) == 0, warnings


def propose_python_execution(code: str) -> Dict:
    """Propose execution — always requires user approval."""
    is_safe, warnings = _is_safe(code)
    lines = len(code.split("\n"))

    return {
        "success":  True,
        "type":     "approval_required",
        "tool":     "python_sandbox",
        "action":   "execute",
        "safe":     is_safe,
        "params":   {"code": code, "timeout": MAX_EXECUTION_TIME},
        "preview":  {
            "lines":    lines,
            "warnings": warnings if warnings else None,
            "blocked":  not is_safe
        }
    }


def execute_python_code(code: str, timeout: int = MAX_EXECUTION_TIME) -> Dict:
    """
    Execute in isolated subprocess.
    Blocks dangerous code before execution.
    """
    is_safe, warnings = _is_safe(code)
    if not is_safe:
        return {
            "success": False,
            "error":   f"Blocked dangerous code: {', '.join(warnings)}",
            "blocked": True
        }

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            # Extra isolation
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"}
        )

        output = result.stdout[:MAX_OUTPUT_SIZE]
        error  = result.stderr[:MAX_OUTPUT_SIZE] if result.returncode != 0 else None

        return {
            "success":     result.returncode == 0,
            "output":      output,
            "error":       error,
            "return_code": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass  # TODO: handle


def extract_python_code(text: str) -> Optional[str]:
    match = re.search(r'```(?:python)?\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    if any(kw in text for kw in ["def ", "import ", "print(", "for ", "if __name__"]):
        return text.strip()
    return None
