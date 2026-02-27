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

