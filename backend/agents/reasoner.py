#==========================================
# astra_engine/agents/reasoner.py
# ==========================================

import re

def reason(user_text: str) -> str:
    """
    Pre-process user input to clarify ambiguous queries.
    Makes questions more specific before sending to LLM.
    """
    if not user_text:
        return user_text
        
    txt = user_text.strip()

    # Single word queries → make explicit
    if len(txt.split()) == 1 and txt.isalpha():
        return f"Tell me about {txt}."

    # Short questions with just "?" → expand
    if len(txt.split()) <= 2 and "?" in txt:
        topic = txt.replace("?", "").strip()
        return f"Explain {topic} briefly."

    # Fix spacing
    txt = re.sub(r"\s+", " ", txt)

    return txt
