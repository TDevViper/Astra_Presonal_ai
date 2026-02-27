
# ==========================================
# astra_engine/utils/cleaner.py
# ==========================================

import re

def clean_text(text: str) -> str:
    """
    Clean and normalize text input.
    - Strip whitespace
    - Remove unusual characters
    - Normalize spacing
    """
    if not isinstance(text, str):
        return ""
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    # Remove control characters but keep normal punctuation
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    
    return text
