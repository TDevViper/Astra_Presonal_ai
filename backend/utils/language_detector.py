
# ==========================================
# astra_engine/utils/language_detector.py (NEW)
# ==========================================

def detect_language(text: str) -> str:
    """
    Detect if user is writing in Hindi (Devanagari or Hinglish).
    Returns: 'hindi', 'hinglish', or 'english'
    """
    # Devanagari script detection (Unicode range)
    devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    if devanagari_chars > 0:
        return 'hindi'

    # Hinglish keyword detection (Hindi words in Roman script)
    hinglish_keywords = [
        'kya', 'hai', 'hain', 'mein', 'main', 'ho', 'tum', 'aap',
        'kaise', 'kaisa', 'nahi', 'haan', 'accha', 'theek', 'baat',
        'karo', 'karna', 'chahiye', 'mujhe', 'tumhe', 'apna', 'mera',
        'tera', 'uska', 'humara', 'yahan', 'wahan', 'batao', 'bolo',
        'samjho', 'dekho', 'suno', 'zaroor', 'bilkul', 'bahut',
        'thoda', 'zyada', 'abhi', 'phir', 'lekin', 'aur', 'ya',
        'matlab', 'kyun', 'kab', 'kahan', 'kaun', 'kitna', 'kitni'
    ]
    text_words = text.lower().split()
    hindi_word_count = sum(1 for w in text_words if w in hinglish_keywords)

    if hindi_word_count >= 2:
        return 'hinglish'
    if hindi_word_count == 1 and len(text_words) <= 5:
        return 'hinglish'

    return 'english'


def get_language_instruction(language: str) -> str:
    """Get system prompt instruction based on detected language."""
    if language == 'hindi':
        return "\nLANGUAGE: User is writing in Hindi (Devanagari). Respond ONLY in Hindi (Devanagari script).\n"
    elif language == 'hinglish':
        return "\nLANGUAGE: User is writing in Hinglish (Hindi using Roman letters). Respond in Hinglish - casual Hindi using Roman letters, like a friend would text.\n"
    return ""