import re

INTENT_WORD_LIMITS = {
    "code":      450,
    "debug":     450,
    "technical": 200,
    "explain":   180,
    "research":  280,
    "search":    250,
    "list":      200,
    "casual":    40,
    "greeting":  20,
    "default":   60,
}

TECHNICAL_KEYWORDS = [
    "code", "function", "class", "error", "bug", "fix", "implement",
    "script", "debug", "install", "configure", "api", "database",
    "python", "javascript", "bash", "terminal", "command", "git",
    "deploy", "server", "build", "compile", "stack", "library"
]

CASUAL_KEYWORDS = [
    "hi", "hello", "hey", "thanks", "ok", "okay", "sure", "cool",
    "how are you", "whats up", "good morning", "good night"
]

def detect_intent_for_limit(text: str) -> str:
    text_lower = text.lower()
    if any(k in text_lower for k in CASUAL_KEYWORDS):
        return "casual"
    if any(k in text_lower for k in TECHNICAL_KEYWORDS):
        return "technical"
    if "explain" in text_lower or "what is" in text_lower:
        return "explain"
    if "search" in text_lower or "find" in text_lower or "latest" in text_lower:
        return "search"
    if "list" in text_lower or "give me" in text_lower:
        return "list"
    return "default"

def limit_words(text: str, max_words: int = None, intent: str = None) -> str:
    if intent is None:
        intent = "default"
    limit = max_words or INTENT_WORD_LIMITS.get(intent, INTENT_WORD_LIMITS["default"])
    words = text.split()
    if len(words) <= limit:
        return text
    truncated = " ".join(words[:limit])
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")
    cut_at = max(last_period, last_newline)
    if cut_at > int(limit * 0.75 * 5):
        return truncated[:cut_at + 1]
    return truncated + "..."
