import logging
import ollama
import os

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
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


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
                r = r[idx + 1:].strip()
                break
    return r


def _llm_review(reply: str, user_input: str, user_name: str, model: str) -> str:
    prompt = f"""You are a response editor for an AI assistant called ASTRA.
Review the reply below and fix ONLY these issues:
- Remove filler openers ("Sure!", "Certainly!", "Great question!", etc.)
- Remove unnecessary repetition of the user's question
- Trim to under 200 words if it's bloated, keeping all key facts
- Fix any obvious factual contradiction with the question asked

User asked: {user_input}
Reply to review:
{reply}

Output ONLY the corrected reply. No commentary. No preamble. If the reply is already good, output it unchanged."""
    try:
        client   = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 300}
        )
        result = response["message"]["content"].strip()
        # Safety: reject if LLM returned something suspiciously short or ballooned
        if len(result) < 10 or len(result) > len(reply) * 2:
            logger.warning("Critic LLM output suspicious, keeping original")
            return reply
        return result
    except Exception as e:
        logger.warning(f"Critic LLM failed ({e}), falling back to fast fix")
        return _fast_fix(reply)


def critic_review(reply, user_name, memory, user_input="", model=None, intent="general"):
    if not reply or len(reply.strip()) < 5:
        return reply

    if not _needs_review(reply, intent):
        return reply

    # Try fast fix first (no LLM cost)
    fast = _fast_fix(reply)
    if fast != reply and len(fast) > 20:
        logger.info("Critic: filler stripped (fast path)")
        return fast

    # Full LLM review for long or complex replies
    _model = model or os.getenv("DEFAULT_MODEL", "phi3:mini")
    logger.info(f"Critic: running LLM review with {_model}")
    return _llm_review(reply, user_input, user_name, _model)
