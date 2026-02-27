
# ==========================================
# astra_engine/agents/critic.py
# ==========================================

import re

def critic_review(reply: str, user_name: str, memory: dict) -> str:
    """
    Post-processing critic that fixes:
    1. Name hallucinations (calling user 'friend')
    2. Over-verbose responses
    3. Repetitive phrases
    4. Wrong pronouns
    """
    if not reply:
        return reply
    
    # 1. Fix name hallucination
    reply = re.sub(
        r'\b(friend|buddy|pal)\b',
        user_name,
        reply,
        flags=re.IGNORECASE
    )
    
    # 2. Shorten if too verbose (over 80 words)
    words = reply.split()
    if len(words) > 80:
        reply = " ".join(words[:80]) + "..."
    
    # 3. Remove repetitive filler phrases
    banned_phrases = [
        "you, friend",
        "dear friend",
        "my friend",
        "hey friend"
    ]
    for phrase in banned_phrases:
        reply = reply.replace(phrase, user_name)
    
    # 4. Fix double spaces
    reply = re.sub(r'\s+', ' ', reply)
    
    # 5. Ensure proper capitalization
    if reply and reply[0].islower():
        reply = reply[0].upper() + reply[1:]
    
    return reply.strip()


def critic(user_input: str) -> str:
    """Standalone critic function (if called directly)."""
    return f"Critique: {user_input}"

