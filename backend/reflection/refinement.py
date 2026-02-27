#==========================================
# FIX 2: astra_engine/reflection/refinement.py
# Stop adding name to every response
# ==========================================

from utils.cleaner import clean_text
from utils.polisher import polish_reply
from utils.limiter import limit_words


def refine_reply(text: str, memory: dict, user_name: str) -> str:
    """
    Final refinement:
    1. Fix pronoun issues
    2. Remove awkward name appending
    3. Personalize only when relevant
    """
    if not text:
        return text

    reply = text.strip()

    # 1. FIX "ASTRA" self-references → "I"
    import re
    reply = re.sub(r'\bASTRA\b(?!\s*ENGINE|\s*v)', 'I', reply)
    reply = re.sub(r'\bASTRA\'s\b', 'my', reply)

    # 2. FIX friend/buddy → user_name
    reply = re.sub(r'\b(friend|buddy|pal)\b', user_name, reply, flags=re.IGNORECASE)
    reply = reply.replace("you, friend", f"you, {user_name}")

    # 3. REMOVE "Arnav." tacked onto end (just the name alone)
    # Only remove if it's just the name added as filler at the very end
    reply = re.sub(rf'\s+{re.escape(user_name)}\.$', '.', reply)
    reply = re.sub(rf',\s+{re.escape(user_name)}\.$', '.', reply)
    reply = re.sub(rf'\s+{re.escape(user_name)}!$', '!', reply)

    # 4. Clean double spaces
    reply = re.sub(r'\s+', ' ', reply).strip()

    # 5. PERSONALIZE only for short casual replies (not technical)
    technical_keywords = [
        'algorithm', 'neural', 'network', 'model', 'architecture',
        'function', 'process', 'system', 'mechanism', 'transformer',
        'attention', 'gradient', 'optimize', 'compute', 'data'
    ]
    is_technical = any(kw in reply.lower() for kw in technical_keywords)
    is_long = len(reply.split()) > 25

    # Don't add name if: technical, long, already has name, or is a question
    has_name = user_name.lower() in reply.lower()
    ends_with_q = reply.endswith("?")

    if not is_technical and not is_long and not has_name and not ends_with_q:
        # Only add name ~30% of the time for casual responses
        import random
        if random.random() < 0.3:
            reply = reply.rstrip('.!') + f", {user_name}!"

    # 6. FINAL POLISH
    reply = limit_words(reply, max_words=80)
    reply = polish_reply(reply)

    return reply


