import threading
from functools import wraps


def timeout(seconds: int = 30):
    """
    Thread-safe timeout decorator using threading.Timer.
    Works inside Flask streaming threads unlike signal.SIGALRM.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result    = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            t = threading.Thread(target=target)
            t.start()
            t.join(timeout=seconds)

            if t.is_alive():
                return {
                    "reply":            "That took too long — try a simpler question.",
                    "intent":           "timeout",
                    "agent":            "timeout_handler",
                    "confidence":       0.0,
                    "confidence_label": "LOW",
                    "confidence_emoji": "🔴",
                    "emotion":          "neutral",
                    "tool_used":        False,
                    "memory_updated":   False,
                    "elapsed":          float(seconds),
                }

            if exception[0]:
                raise exception[0]

            return result[0]
        return wrapper
    return decorator
