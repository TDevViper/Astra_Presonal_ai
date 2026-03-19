#==========================================
# astra_engine/memory/memory_engine.py
# ==========================================
import json
import copy
import os
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(BASE_DIR, "memory", "data", "memory.json")
LOCK_FILE   = os.path.join(BASE_DIR, "memory", "data", "memory.lock")

_thread_lock  = threading.Lock()

# In-memory cache — eliminates disk read on every request (P-2)
_memory_cache: Dict[str, Any] = {}
_cache_valid  = False
_CACHE_MAX_AGE = 30  # seconds — re-read from disk if file changes externally

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
    """Load memory — returns from in-memory cache if fresh, else reads disk."""
    global _memory_cache, _cache_valid
    with _thread_lock:
        # Return cached copy if valid
        if _cache_valid and _memory_cache:
            return copy.deepcopy(_memory_cache)
        # Cache miss — read from disk
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    _acquire_flock(f, shared=True)
                    memory = json.load(f)
                for key in DEFAULT_MEMORY:
                    if key not in memory:
                        memory[key] = DEFAULT_MEMORY[key]
                _memory_cache = memory
                _cache_valid  = True
                return copy.deepcopy(memory)
            except json.JSONDecodeError:
                logger.error("Memory file corrupted, resetting to default")
                return DEFAULT_MEMORY.copy()
            except Exception as e:
                logger.error(f"Error loading memory: {e}")
                return copy.deepcopy(DEFAULT_MEMORY)
        return copy.deepcopy(DEFAULT_MEMORY)


def save_memory(memory: Dict[str, Any], history: list = None) -> bool:
    """Save memory to disk and update in-memory cache atomically."""
    global _memory_cache, _cache_valid
    with _thread_lock:
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            tmp = MEMORY_FILE + ".tmp"
            with open(tmp, 'w', encoding='utf-8') as f:
                _acquire_flock(f, shared=False)
                json.dump(memory, f, indent=2, ensure_ascii=False)
            os.replace(tmp, MEMORY_FILE)
            # Update cache immediately — no stale reads after save
            _memory_cache = copy.deepcopy(memory)
            _cache_valid  = True
            return True
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            _cache_valid = False  # force re-read on next load
            return False


def invalidate_memory_cache():
    """Force next load_memory() to re-read from disk."""
    global _cache_valid
    with _thread_lock:
        _cache_valid = False


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
