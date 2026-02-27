 #==========================================
# astra_engine/utils/limiter.py
# ==========================================

def limit_words(text: str, max_words: int = 100) -> str:
    """
    Limit text to maximum number of words.
    Adds ellipsis if truncated.
    """
    if not text:
        return text
    
    words = text.split()
    
    if len(words) <= max_words:
        return text
    
    # Truncate and add ellipsis
    truncated = " ".join(words[:max_words])
    
    # If last character is punctuation, remove it before ellipsis
    if truncated[-1] in ',.;:':
        truncated = truncated[:-1]
    
    return truncated + "..."


def limit_chars(text: str, max_chars: int = 500) -> str:
    """Limit text to maximum characters."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + "..."