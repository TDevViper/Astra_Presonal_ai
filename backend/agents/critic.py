import logging
import ollama
from typing import Dict

logger = logging.getLogger(__name__)

_MIN_REVIEW_LEN = 40
_SKIP_INTENTS = {
    "shortcut", "memory_storage", "calendar", "whatsapp",
    "system_control", "git_operation", "task_management",
    "web_search", "file_operation", "python_execution_proposal",
}
_FILLER_STARTERS = [
    "sure!", "certainly!", "of course!", "great question",
    "absolutely!", "i'd be happy to", "happy to help",
    "i'm happy to", "of course, i", "great, let me",
]


def _needs_review(reply: str, intent: str) -> bool:
    if intent in _SKIP_INTENTS:
        return False
    if len(reply.strip()) < _MIN_REVIEW_LEN:
        return False
    r = reply.lower()
    return any(r.startswith(f) for f in _FILLER_STARTERS) or len(reply.split()) > 300


def _fast_fix(reply: str) -> str:
    r = reply.strip()
    for filler in _FILLER_STARTERS:
        if r.lower().startswith(filler):
            idx = r.find(".")
            if 0 < idx < 80:
                r = r[idx+1:].strip()
                break
    return r


def critic_review(reply, user_name, memory, user_input="", model=None, intent="general"):
    if not reply or len(reply.strip()) < 5:
        return reply
    if not _needs_review(reply, intent):
        return reply

    fixed = _fast_fix(reply)
    if fixed != reply and len(fixed) > 20:
        logger.info("Critic: filler stripped (no LLM)")
        return fixed

    selected_model = model or "phi3:mini"
    try:
        prompt = f"""Review this AI reply. Fix ONLY if clearly padded or wrong. Return unchanged if fine.

Question: {user_input[:150]}
Reply: {reply[:500]}

Output ONLY the final reply text, no preamble:"""

        response = ollama.chat(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 200},
        )
        result = response["message"]["content"].strip()
        if not result or len(result) < 5:
            return reply

        orig_words   = set(reply.lower().split())
        result_words = set(result.lower().split())
        overlap      = len(orig_words & result_words) / max(len(orig_words), 1)
        if overlap < 0.3:
            return reply

        return result
    except Exception as e:
        logger.warning(f"Critic failed ({e})")
        return reply
