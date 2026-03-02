# ==========================================
# astra_engine/utils/limiter.py
# ==========================================

# Technical keywords that deserve longer responses
_TECHNICAL_KEYWORDS = [
    'algorithm', 'function', 'code', 'class', 'import', 'error', 'debug',
    'neural', 'model', 'architecture', 'database', 'api', 'async', 'loop',
    'variable', 'syntax', 'library', 'framework', 'install', 'config',
    'docker', 'git', 'server', 'deploy', 'memory', 'cpu', 'gpu', 'network'
]

def _is_technical(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _TECHNICAL_KEYWORDS)

def limit_words(text: str, max_words: int = 100) -> str:
    """
    Context-aware word limiter.
    - Technical responses get up to 200 words
    - Code blocks are never truncated mid-block
    - Casual responses stay concise (max_words)
    """
    if not text:
        return text

    # Never truncate if contains code blocks
    if "```" in text:
        return text

    words = text.split()

    # Give technical responses more room
    effective_max = 200 if _is_technical(text) else max_words

    if len(words) <= effective_max:
        return text

    truncated = " ".join(words[:effective_max])

    # Cut at last sentence boundary if possible
    for punct in ['. ', '! ', '? ']:
        last_sentence = truncated.rfind(punct)
        if last_sentence > effective_max * 3:  # at least 75% through
            return truncated[:last_sentence + 1]

    if truncated[-1] in ',.;:':
        truncated = truncated[:-1]

    return truncated + "..."


def limit_chars(text: str, max_chars: int = 500) -> str:
    """Limit text to maximum characters."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + "..."