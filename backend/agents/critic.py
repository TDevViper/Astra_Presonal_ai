# ==========================================
# agents/critic.py — v2.0 (LLM-powered)
# ==========================================

import re
import logging
import ollama

logger = logging.getLogger(__name__)

_LLM_CRITIC_MIN_WORDS = 30

_BANNED_PHRASES = [
    "you, friend", "dear friend", "my friend", "hey friend",
    "as an AI language model", "I cannot help with",
    "I'd be happy to help you with that",
    "Certainly!", "Absolutely!", "Of course!"
]


def _fast_fix(reply: str, user_name: str) -> str:
    if not reply:
        return reply

    reply = re.sub(r'\bASTRA\b(?!\s*ENGINE|\s*v)', 'I', reply)
    reply = re.sub(r"\bASTRA's\b", 'my', reply)
    reply = re.sub(r'\b(friend|buddy|pal)\b', user_name, reply, flags=re.IGNORECASE)

    for phrase in _BANNED_PHRASES:
        reply = reply.replace(phrase, "")

    reply = re.sub(rf'\s+{re.escape(user_name)}[.!]?$', '.', reply)
    reply = re.sub(rf',\s+{re.escape(user_name)}[.!]?$', '.', reply)
    reply = re.sub(r'\s+', ' ', reply).strip()

    if reply and reply[0].islower():
        reply = reply[0].upper() + reply[1:]

    return reply


def _llm_critic(reply: str, user_input: str, user_name: str,
                model: str = "phi3:mini") -> str:
    prompt = f"""You are a quality critic for an AI assistant called ASTRA.

Review this reply and fix ONLY genuine problems:
- Factual contradictions
- Repetition of the same point
- Awkward or unnatural phrasing
- Starting with filler like "Certainly!" or "Of course!"
- Replies that don't actually answer the question

If the reply is already good, return it unchanged.
Return ONLY the fixed reply — no commentary.

User asked: {user_input}
Reply to review: {reply}

Fixed reply:"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_predict": 200}
        )
        improved = response["message"]["content"].strip()

        original_words = len(reply.split())
        improved_words = len(improved.split())

        if improved_words < 3 or improved_words > original_words * 2:
            logger.warning("LLM critic output suspicious, keeping original")
            return reply

        logger.info("✅ LLM critic improved reply")
        return improved

    except Exception as e:
        logger.warning(f"LLM critic failed ({e}), using original")
        return reply


def critic_review(reply: str, user_name: str, memory: dict,
                  user_input: str = "", model: str = "phi3:mini") -> str:
    if not reply:
        return reply

    reply = _fast_fix(reply, user_name)

    word_count = len(reply.split())
    if user_input and word_count >= _LLM_CRITIC_MIN_WORDS:
        logger.info(f"🔍 LLM critic running on {word_count}-word reply")
        reply = _llm_critic(reply, user_input, user_name, model=model)

    return reply.strip()


def critic(user_input: str) -> str:
    return user_input
