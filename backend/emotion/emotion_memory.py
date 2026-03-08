#==========================================
# astra_engine/emotion/emotion_memory.py
# ==========================================

from typing import Dict
from datetime import datetime


def ensure_emotion_memory(memory: Dict) -> Dict:
    """
    Ensure emotion memory structure exists in memory dict.
    Creates default structure if missing.
    """
    if "emotional_patterns" not in memory:
        memory["emotional_patterns"] = {}

    patterns = memory["emotional_patterns"]

    # Set defaults
    patterns.setdefault("last_emotion", {"label": "neutral", "score": 0.0})
    patterns.setdefault("history", [])
    patterns.setdefault("emotion_stats", {})

    memory["emotional_patterns"] = patterns
    return memory


def update_emotion(memory: Dict, emotion_label: str, score: float) -> Dict:
    """
    Update emotion memory with new detection.
    
    Args:
        memory: Memory dict
        emotion_label: Detected emotion
        score: Confidence score
        
    Returns:
        Updated memory dict
    """
    memory = ensure_emotion_memory(memory)
    patterns = memory["emotional_patterns"]

    # Update last emotion
    patterns["last_emotion"] = {
        "label": emotion_label,
        "score": float(score),
        "timestamp": datetime.utcnow().isoformat()
    }

    # Add to history
    patterns["history"].append({
        "label": emotion_label,
        "score": float(score),
        "timestamp": datetime.utcnow().isoformat()
    })

    # Keep only last 30 emotions
    if len(patterns["history"]) > 30:
        patterns["history"] = patterns["history"][-30:]

    # Update statistics
    if emotion_label not in patterns["emotion_stats"]:
        patterns["emotion_stats"][emotion_label] = {"count": 0, "avg_score": 0.0}
    
    stats = patterns["emotion_stats"][emotion_label]
    old_count = stats["count"]
    old_avg = stats["avg_score"]
    
    # Update running average
    stats["count"] = old_count + 1
    stats["avg_score"] = ((old_avg * old_count) + score) / stats["count"]
    
    patterns["emotion_stats"][emotion_label] = stats
    memory["emotional_patterns"] = patterns

    return memory


def get_emotion(memory: Dict) -> Dict:
    """Get last detected emotion."""
    memory = ensure_emotion_memory(memory)
    return memory["emotional_patterns"]["last_emotion"]


def get_dominant_emotion(memory: Dict) -> str:
    """Get most frequent emotion from history."""
    memory = ensure_emotion_memory(memory)
    stats = memory["emotional_patterns"].get("emotion_stats", {})
    
    if not stats:
        return "neutral"
    
    # Find emotion with highest count
    dominant = max(stats.items(), key=lambda x: x[1]["count"])
    return dominant[0]



# ── Cross-session persistent emotion tracking ─────────────────
import json as _json
import os as _os
from datetime import datetime as _dt
from collections import Counter as _Counter

_BACKEND_DIR2        = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
EMOTION_HISTORY_FILE = _os.path.join(_BACKEND_DIR2, "memory", "data", "emotion_history.json")


def log_emotion_persistent(emotion: str, context: str, user_name: str = "Arnav"):
    history = _load_emotion_history()
    history.append({
        "timestamp": _dt.now().isoformat(),
        "emotion":   emotion,
        "context":   context[:100],
        "user":      user_name
    })
    _save_emotion_history(history[-200:])


def get_emotional_trend(last_n: int = 50) -> str:
    history = _load_emotion_history()
    if not history:
        return "No emotional history yet."
    counts = _Counter(e["emotion"] for e in history[-last_n:])
    top    = counts.most_common(3)
    return "Emotional pattern: " + ", ".join(f"{e}({c}x)" for e, c in top)


def inject_emotional_context(system_prompt: str) -> str:
    return system_prompt + f"\nEmotional context: {get_emotional_trend()}"


def _load_emotion_history():
    if not _os.path.exists(EMOTION_HISTORY_FILE):
        return []
    try:
        with open(EMOTION_HISTORY_FILE) as f:
            return _json.load(f)
    except Exception:
        return []


def _save_emotion_history(history):
    _os.makedirs(_os.path.dirname(EMOTION_HISTORY_FILE), exist_ok=True)
    with open(EMOTION_HISTORY_FILE, "w") as f:
        _json.dump(history, f, indent=2)

# ── Persistent cross-session emotion tracking (appended by upgrade) ────
import json as _json, os as _os
from datetime import datetime as _dt
from collections import Counter as _Counter

_EMOTION_FILE = "backend/memory/data/emotion_history.json"

def log_emotion_persistent(emotion: str, context: str, user_name: str = "Arnav"):
    history = _load_emotion_history()
    history.append({
        "timestamp": _dt.now().isoformat(),
        "emotion":   emotion,
        "context":   context[:100],
        "user":      user_name
    })
    _save_emotion_history(history[-200:])

def get_emotional_trend(days: int = 7) -> str:
    history  = _load_emotion_history()
    recent   = history[-50:]
    emotions = [e["emotion"] for e in recent]
    counts   = _Counter(emotions)
    top      = counts.most_common(3)
    return "Emotional pattern: " + ", ".join([f"{e}({c}x)" for e, c in top])

def inject_emotional_context(system_prompt: str) -> str:
    return system_prompt + f"\nEmotional context: {get_emotional_trend()}"

def _load_emotion_history():
    _os.makedirs(_os.path.dirname(_EMOTION_FILE), exist_ok=True)
    if not _os.path.exists(_EMOTION_FILE):
        return []
    try:
        with open(_EMOTION_FILE) as f:
            return _json.load(f)
    except Exception:
        return []

def _save_emotion_history(history):
    with open(_EMOTION_FILE, "w") as f:
        _json.dump(history, f, indent=2)
