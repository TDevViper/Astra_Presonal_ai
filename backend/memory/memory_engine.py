# ==========================================
# memory/memory_engine.py — v6.1
# Multi-user isolated memory.
# Fully backward compatible:
#   load_memory()           → default user
#   load_memory("alice")    → alice's memory
# MEMORY_FILE kept so tests can monkeypatch it.
# _CACHE_MAX_AGE TTL now actually enforced.
# ==========================================
import json
import copy
import os
import time
import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "memory", "data", "users")
MEMORY_FILE = os.path.join(DATA_DIR, "default", "memory.json")
LOCK_FILE = MEMORY_FILE + ".lock"

_thread_lock = threading.Lock()
_CACHE_MAX_AGE = 30

_user_caches: Dict[str, Dict[str, Any]] = {}

DEFAULT_MEMORY = {
    "user_facts": [],
    "preferences": {"name": "User", "location": None, "favorite_color": None},
    "conversation_summary": [],
    "emotional_patterns": {
        "last_emotion": {"label": "neutral", "score": 0.0},
        "history": [],
        "emotion_stats": {},
    },
}


def _resolve_path(user_id: str = "default") -> str:
    if user_id == "default":
        return MEMORY_FILE
    safe = "".join(c for c in user_id if c.isalnum() or c in "-_")[:64] or "default"
    return os.path.join(DATA_DIR, safe, "memory.json")


def _cache_get(user_id: str) -> Optional[Dict]:
    c = _user_caches.get(user_id)
    if c and c.get("valid") and (time.time() - c.get("ts", 0)) < _CACHE_MAX_AGE:
        return copy.deepcopy(c["data"])
    return None


def _cache_set(user_id: str, data: Dict):
    _user_caches[user_id] = {
        "data": copy.deepcopy(data),
        "ts": time.time(),
        "valid": True,
    }


def _cache_invalidate(user_id: str):
    if user_id in _user_caches:
        _user_caches[user_id]["valid"] = False


def load_memory(user_id: str = "default") -> Dict[str, Any]:
    with _thread_lock:
        cached = _cache_get(user_id)
        if cached is not None:
            return cached
        mem_file = _resolve_path(user_id)
        if os.path.exists(mem_file):
            try:
                with open(mem_file, "r", encoding="utf-8") as f:
                    _acquire_flock(f, shared=True)
                    memory = json.load(f)
                for key in DEFAULT_MEMORY:
                    if key not in memory:
                        memory[key] = copy.deepcopy(DEFAULT_MEMORY[key])
                _cache_set(user_id, memory)
                return copy.deepcopy(memory)
            except json.JSONDecodeError:
                logger.error("Memory corrupted for user=%s, resetting", user_id)
            except Exception as e:
                logger.error("load_memory user=%s: %s", user_id, e)
        return copy.deepcopy(DEFAULT_MEMORY)


def save_memory(
    memory: Dict[str, Any], user_id: str = "default", history: list = None
) -> bool:
    with _thread_lock:
        try:
            mem_file = _resolve_path(user_id)
            os.makedirs(os.path.dirname(mem_file), exist_ok=True)
            tmp = mem_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                _acquire_flock(f, shared=False)
                json.dump(memory, f, indent=2, ensure_ascii=False)
            os.replace(tmp, mem_file)
            _cache_set(user_id, memory)
            return True
        except Exception as e:
            logger.error("save_memory user=%s: %s", user_id, e)
            _cache_invalidate(user_id)
            return False


def invalidate_memory_cache(user_id: str = "default"):
    with _thread_lock:
        _cache_invalidate(user_id)


def _acquire_flock(f, shared: bool):
    try:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
    except ImportError:
        pass


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
