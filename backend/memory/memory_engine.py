#==========================================
# astra_engine/memory/memory_engine.py
# ==========================================
import json
import os
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(BASE_DIR, "memory", "data", "memory.json")
LOCK_FILE   = os.path.join(BASE_DIR, "memory", "data", "memory.lock")

_thread_lock = threading.Lock()

DEFAULT_MEMORY = {
    "user_facts": [],
    "preferences": {
        "name": "User",
        "location": None,
        "favorite_color": None
    },
    "conversation_summary": [],
    "emotional_patterns": {
        "last_emotion": {"label": "neutral", "score": 0.0},
        "history": [],
        "emotion_stats": {}
    }
}


def load_memory() -> Dict[str, Any]:
    """Load memory from file with file + thread locking."""
    with _thread_lock:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    _acquire_flock(f, shared=True)
                    memory = json.load(f)
                for key in DEFAULT_MEMORY:
                    if key not in memory:
                        memory[key] = DEFAULT_MEMORY[key]
                return memory
            except json.JSONDecodeError:
                logger.error("Memory file corrupted, resetting to default")
                return DEFAULT_MEMORY.copy()
            except Exception as e:
                logger.error(f"Error loading memory: {e}")
                return DEFAULT_MEMORY.copy()
        return DEFAULT_MEMORY.copy()


def save_memory(memory: Dict[str, Any], history: list = None) -> bool:
    """Save memory to file with file + thread locking."""
    with _thread_lock:
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            tmp = MEMORY_FILE + ".tmp"
            with open(tmp, 'w', encoding='utf-8') as f:
                _acquire_flock(f, shared=False)
                json.dump(memory, f, indent=2, ensure_ascii=False)
            os.replace(tmp, MEMORY_FILE)
            return True
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False


def _acquire_flock(f, shared: bool):
    """Apply fcntl file lock on supported platforms (Linux/macOS)."""
    try:
        import fcntl
        mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        fcntl.flock(f.fileno(), mode)
    except ImportError:
        pass  # Windows — skip flock, thread lock still protects


def update_memory(memory: dict, category: str, key: "str | None" = None, value=None):
    if category not in memory:
        memory[category] = [] if category == "user_facts" else {}

    if category == "user_facts":
        if isinstance(value, dict):
            memory["user_facts"].append(value)
    else:
        if key is None:
            raise ValueError("key required for non-list categories")
        if not isinstance(memory[category], dict):
            memory[category] = {}
        memory[category][key] = value

    return memory
