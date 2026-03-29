import ast, subprocess, tempfile, os, logging, re, resource
from typing import Dict

logger = logging.getLogger(__name__)

_MAX_EXEC_SECONDS = 10
_MAX_OUTPUT_CHARS = 3000
_MAX_INPUT_CHARS  = 8000

_BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "socket", "requests",
    "urllib", "http", "ftplib", "smtplib", "importlib", "ctypes",
    "pickle", "marshal", "pathlib", "glob", "pty", "tty", "termios",
    "signal", "threading", "multiprocessing", "concurrent",
}

_BLOCKED_BUILTINS = {"__import__", "exec", "eval", "open", "compile", "breakpoint"}

def _code_execution_allowed() -> bool:
    """Single source of truth for code execution permission."""
    return os.getenv("ALLOW_CODE_EXECUTION", "false").lower() == "true"


def extract_python_code(text: str) -> str:
    m = re.search(r'```python\s*(.*?)```', text, re.DOTALL)
    return m.group(1).strip() if m else ""

def _is_safe(code: str) -> tuple[bool, str]:
    if len(code) > _MAX_INPUT_CHARS:
        return False, f"Code too long (max {_MAX_INPUT_CHARS} chars)"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                if name.split(".")[0] in _BLOCKED_IMPORTS:
                    return False, f"Blocked import: '{name}'"
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_BUILTINS:
                return False, f"Blocked builtin: '{node.func.id}'"
        if isinstance(node, ast.Attribute) and node.attr in {
            "__class__", "__bases__", "__subclasses__", "__globals__", "__builtins__", "__import__"
        }:
            return False, f"Blocked dunder: '{node.attr}'"
    return True, ""

def propose_python_execution(code: str) -> Dict:
    safe, reason = _is_safe(code)
    if not safe:
        return {"success": False, "code": code, "output": f"Blocked: {reason}",
                "approved": False, "requires_approval": False}
    return {"success": True, "code": code, "output": None,
            "approved": False, "requires_approval": True}

def _set_limits():
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    except Exception as _e:
        logger.debug('sandbox: %s', _e)

def execute_python(code: str) -> Dict:
    safe, reason = _is_safe(code)
    if not safe:
        return {"success": False, "output": f"Blocked: {reason}", "error": reason}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, prefix='astra_sandbox_') as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ["python3", "-I", "-S", tmp_path],
            capture_output=True, text=True,
            timeout=_MAX_EXEC_SECONDS,
            preexec_fn=_set_limits,
        )
        output = (result.stdout + result.stderr).strip()
        if len(output) > _MAX_OUTPUT_CHARS:
            output = output[:_MAX_OUTPUT_CHARS] + "\n... (truncated)"
        return {"success": result.returncode == 0, "output": output or "(no output)",
                "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": f"Timed out after {_MAX_EXEC_SECONDS}s", "error": "timeout"}
    except Exception as e:
        return {"success": False, "output": str(e), "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception as _e:
            logger.debug('sandbox: %s', _e)

# ── Docker sandbox shim ──────────────────────────────────────────────────────
# Tries Docker container isolation first; falls back to AST sandbox if Docker
# is unavailable (e.g. running outside compose without Docker Desktop).
def _legacy_run_code(code: str) -> dict:  # calls execute_python, NOT itself
    try:
        from tools.docker_sandbox import run_python
        result = run_python(code)
        return {
            "output": result["stdout"],
            "error":  result["error"] or (result["stderr"] if result["exit_code"] != 0 else None),
            "sandbox": "docker",
        }
    except Exception:
        pass  # fall through to legacy below
    return execute_python(code)


# ── Docker sandbox shim ──────────────────────────────────────────────────────
# Tries Docker container isolation first; falls back to AST sandbox if Docker
# is unavailable (e.g. running outside compose without Docker Desktop).
def run_code(code: str) -> dict:
    try:
        from tools.docker_sandbox import run_python
        result = run_python(code)
        return {
            "output": result["stdout"],
            "error":  result["error"] or (result["stderr"] if result["exit_code"] != 0 else None),
            "sandbox": "docker",
        }
    except Exception:
        pass  # fall through to legacy below
    return execute_python(code)

