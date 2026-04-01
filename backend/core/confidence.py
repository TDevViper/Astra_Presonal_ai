# ==========================================
# astra_engine/core/confidence.py
# ==========================================

from typing import Dict

# Confidence scores per agent/intent
CONFIDENCE_MAP = {
    # Hardcoded shortcuts - always correct
    "shortcut": 1.00,
    "intent_handler": 1.00,
    # Memory - user told us directly, highly reliable
    "memory_recall": 0.95,
    "memory": 0.95,
    "memory_storage": 0.95,
    # Web search - real data but LLM summarized it
    "web_search": 0.75,
    "web_search_agent": 0.75,
    # LLM knowledge by model quality
    "ollama/mistral:latest": 0.72,
    "ollama/llama3.2:3b": 0.65,
    "ollama/phi3:mini": 0.60,
    # Intent-based adjustments
    "technical": 0.70,
    "reasoning": 0.68,
    "casual": 0.60,
    "conversational": 0.60,
    # Errors
    "error": 0.00,
    "error_handler": 0.00,
}

CONFIDENCE_LABELS = {
    (0.95, 1.01): ("CERTAIN", "🟢"),
    (0.75, 0.95): ("HIGH", "🟡"),
    (0.50, 0.75): ("MEDIUM", "🟠"),
    (0.25, 0.50): ("LOW", "🔴"),
    (0.00, 0.25): ("UNKNOWN", "⚪"),
}


def score(agent: str, intent: str) -> float:
    """
    Calculate confidence score for a response.
    Checks agent first, then intent as fallback.
    """
    # Direct agent match
    if agent in CONFIDENCE_MAP:
        base = CONFIDENCE_MAP[agent]
    # Intent match
    elif intent in CONFIDENCE_MAP:
        base = CONFIDENCE_MAP[intent]
    # Default
    else:
        base = 0.55

    return round(base, 2)


def label(confidence: float) -> Dict:
    """
    Get human-readable label and emoji for confidence score.
    Returns: {"text": "HIGH", "emoji": "🟡", "score": 0.75}
    """
    for (low, high), (text, emoji) in CONFIDENCE_LABELS.items():
        if low <= confidence < high:
            return {"text": text, "emoji": emoji, "score": confidence}
    return {"text": "UNKNOWN", "emoji": "⚪", "score": confidence}


def bar(confidence: float, width: int = 10) -> str:
    """
    Generate ASCII confidence bar.
    Example: "████████░░ 0.80"
    """
    filled = round(confidence * width)
    empty = width - filled
    return f"{'█' * filled}{'░' * empty} {confidence:.2f}"
