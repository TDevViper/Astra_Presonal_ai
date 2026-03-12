import re
import os
import logging
import ollama

logger = logging.getLogger(__name__)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

_DEEP_REASON_TRIGGERS = [
    "why", "how does", "explain how", "what causes", "difference between",
    "compare", "pros and cons", "should i", "which is better", "analyze",
    "walk me through", "break down", "step by step", "reason", "think"
]
_SIMPLE_TRIGGERS = [
    "hi", "hello", "hey", "thanks", "ok", "bye",
    "what's my name", "who am i", "tell me a joke"
]

def _needs_deep_reason(text: str) -> bool:
    t = text.lower()
    if any(t.startswith(s) or s == t for s in _SIMPLE_TRIGGERS):
        return False
    return any(trigger in t for trigger in _DEEP_REASON_TRIGGERS)

def _basic_clean(text: str) -> str:
    txt = text.strip()
    txt = re.sub(r"\s+", " ", txt)
    if len(txt.split()) == 1 and txt.isalpha():
        return f"Tell me about {txt}."
    if len(txt.split()) <= 2 and "?" in txt:
        topic = txt.replace("?", "").strip()
        return f"Explain {topic} briefly."
    return txt

def reason(user_text: str, model: str = "phi3:mini") -> str:
    if not user_text or not user_text.strip():
        return user_text
    if not _needs_deep_reason(user_text):
        return _basic_clean(user_text)
    logger.info(f"🧠 Deep reasoning pre-process: {user_text[:60]}...")
    prompt = f"""You are a query optimizer for an AI assistant.
Rewrite the user's question as a clear, structured prompt that will
get the BEST possible answer from an LLM.

Rules:
- Keep the core intent exactly the same
- Make it specific and unambiguous
- If multi-part, list parts clearly
- Do NOT answer — only rewrite
- Output ONLY the rewritten query, nothing else

Original: {user_text}
Rewritten:"""
    try:
        client   = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_predict": 120}
        )
        rewritten = response["message"]["content"].strip()
        if len(rewritten) < 5 or len(rewritten) > len(user_text) * 8:
            logger.warning("Reasoner output suspicious, using original")
            return _basic_clean(user_text)
        logger.info(f"✅ Reasoner: {rewritten[:80]}")
        return rewritten
    except Exception as e:
        if "Connection refused" in str(e) or "Errno 61" in str(e):
            logger.error("Ollama not running — run: ollama serve")
        else:
            logger.warning(f"Reasoner LLM failed ({e}), using basic clean")
        return _basic_clean(user_text)
