
# ==========================================
# astra_engine/utils/polisher.py
# ==========================================

import re

def polish_reply(text: str) -> str:
    """
    Final polish to ensure reply is clean:
    - Proper punctuation
    - No trailing junk
    - Proper capitalization
    """
    if not text:
        return text
    
    text = text.strip()
    
    # Remove trailing punctuation artifacts
    text = re.sub(r'[,;:\s]+$', '', text)
    
    # Ensure ends with proper punctuation
    if text and text[-1] not in '.!?':
        text = text + '.'
    
    # Fix multiple punctuation
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\?{2,}', '?', text)
    text = re.sub(r'!{2,}', '!', text)
    
    # Ensure first character is capitalized
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([,.!?;:])\s*([a-zA-Z])', r'\1 \2', text)
    
    return text
