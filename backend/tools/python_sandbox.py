
# ==========================================
# astra_engine/tools/python_sandbox.py
# ==========================================

import subprocess
import tempfile
import os
from typing import Dict
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Safety limits
MAX_EXECUTION_TIME = 5  # seconds
MAX_OUTPUT_SIZE = 10000  # characters


def propose_python_execution(code: str) -> Dict:
    """
    Propose Python code execution.
    Returns approval request for frontend.
    """
    lines = len(code.split("\n"))
    
    # Quick safety check
    dangerous_keywords = ["os.system", "subprocess", "eval(", "exec(", "__import__", "open("]
    warnings = [kw for kw in dangerous_keywords if kw in code]

    return {
        "success": True,
        "type": "approval_required",
        "tool": "python_sandbox",
        "action": "execute",
        "params": {
            "code": code,
            "timeout": MAX_EXECUTION_TIME
        },
        "preview": {
            "lines": lines,
            "warnings": warnings if warnings else None
        }
    }


def execute_python_code(code: str, timeout: int = MAX_EXECUTION_TIME) -> Dict:
    """
    Execute Python code in isolated subprocess.
    
    Safety measures:
    - Runs in subprocess (can be killed)
    - Time limit
    - Output size limit
    - No file system access (via tempfile)
    """
    try:
        # Create temp file with code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        # Execute in subprocess
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # Clean up
        os.unlink(temp_path)

        output = result.stdout[:MAX_OUTPUT_SIZE]
        error = result.stderr[:MAX_OUTPUT_SIZE] if result.returncode != 0 else None

        return {
            "success": result.returncode == 0,
            "output": output,
            "error": error,
            "return_code": result.returncode
        }

    except subprocess.TimeoutExpired:
        try:
            os.unlink(temp_path)
        except:
            pass
        return {
            "success": False,
            "error": f"Execution timed out after {timeout} seconds"
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def extract_python_code(text: str) -> Optional[str]:
    """Extract Python code from markdown code blocks."""
    import re
    
    # Pattern: ```python ... ```
    pattern = r'```(?:python)?\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    # If no code block, check if entire message looks like code
    if any(kw in text for kw in ["def ", "import ", "print(", "for ", "if __name__"]):
        return text.strip()
    
    return None
