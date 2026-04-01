# tools/quick_tools.py
# Quick tool handlers for simple, instant responses (calculator, time, etc.)
import re
from typing import Optional, Tuple

MATH_TRIGGERS = ["calculate", "what is", "what's", "how much is", "solve", "compute"]


def _try_math(text: str) -> Optional[str]:
    """Try to evaluate a simple math expression."""
    # Extract numbers and operators
    expr = re.sub(r"[^0-9+\-*/().% ]", "", text)
    expr = expr.strip()
    if not expr or len(expr) < 3:
        return None
    try:
        result = eval(expr, {"__builtins__": {}})  # safe eval with no builtins
        return f"{expr} = {result}"
    except Exception:
        return None


def handle_quick_tool(user_input: str) -> Optional[Tuple[str, str, str]]:
    """
    Returns (reply, intent, agent) for quick matches, or None.
    """
    text = user_input.lower().strip()

    # ── Date/time ──────────────────────────────────────────────────────────
    if any(
        w in text
        for w in [
            "what time",
            "current time",
            "what's the time",
            "what date",
            "today's date",
        ]
    ):
        from datetime import datetime

        now = datetime.now()
        if "date" in text:
            reply = f"Today is {now.strftime('%A, %B %d, %Y')}."
        else:
            reply = f"It's {now.strftime('%I:%M %p')} right now."
        return (reply, "time_query", "quick_tools")

    # ── Simple math ────────────────────────────────────────────────────────
    if any(w in text for w in MATH_TRIGGERS):
        result = _try_math(user_input)
        if result:
            return (result, "math", "calculator")

    # ── Inline math expression (no trigger word needed) ───────────────────
    if re.match(r"^[\d\s+\-*/().%]+$", text) and any(
        op in text for op in ["+", "-", "*", "/", "%"]
    ):
        result = _try_math(text)
        if result:
            return (result, "math", "calculator")

    return None
