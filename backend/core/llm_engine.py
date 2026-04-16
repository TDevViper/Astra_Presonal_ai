import logging
import re
import os
import threading
from typing import Generator, List, Dict
import ollama


def _cloud_fallback(prompt: str, system: str = "") -> str:
    import config as cfg

    if cfg.FALLBACK_ANTHROPIC_KEY:
        import urllib.request
        import json

        payload = json.dumps(
            {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": cfg.FALLBACK_ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["content"][0]["text"]
    raise RuntimeError("No cloud fallback configured")


logger = logging.getLogger(__name__)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


def _client():
    return ollama.Client(host=OLLAMA_HOST)


# Removed _HARD_STOP — it fights against model fine-tuning (E-1 audit finding).
# Quality constraints belong in the system prompt built by ContextBuilder,
# not prepended as a meta-instruction that the model must resolve against its training.
_HARD_STOP = (
    ""  # kept as empty string for backward compat, will be removed next cleanup
)

_TOKEN_BUDGETS = {"coding": 1500, "technical": 1200, "reasoning": 800, "research": 1000}

# ── Global TTS worker (single persistent thread) ──
import queue as _queue

_tts_q = _queue.Queue()
_tts_started = False


def _global_tts_worker():
    try:
        from tts_kokoro import speak
    except Exception:
        return
    while True:
        try:
            sentence = _tts_q.get(timeout=1.0)
            if sentence:
                speak(sentence)
            _tts_q.task_done()
        except _queue.Empty:
            continue


def start_tts_worker():
    """Start TTS worker once from lifespan — not at import time."""
    global _tts_started
    if _tts_started:
        return
    import threading as _thr

    _thr.Thread(target=_global_tts_worker, daemon=True, name="tts-worker").start()
    _tts_started = True
    logger.info("🔊 TTS worker started")


class LLMEngine:
    def __init__(self, model_manager):
        self._mm = model_manager

    def try_react(
        self, user_input: str, selected_model: str, context: str, user_name: str
    ) -> str:
        try:
            from agents.react_agent import react, needs_react

            if needs_react(user_input):
                logger.info("⚛️  ReAct triggered")
                reply = react(
                    user_input,
                    model=selected_model,
                    context=context,
                    user_name=user_name,
                )
                if reply and len(reply.split()) >= 10:
                    return reply
        except Exception as e:
            logger.warning("react_agent failed: %s", e)
        return ""

    def call(
        self,
        user_input: str,
        system_prompt: str,
        selected_model: str,
        query_intent: str,
        history: List[Dict],
    ) -> str:
        # Only run reasoner on intents that benefit from it
        processed = user_input
        if query_intent in ("reasoning", "technical", "coding", "analysis"):
            try:
                from agents.reasoner import reason

                processed = reason(user_input, model=selected_model)
            except Exception as e:
                logger.warning("reasoner failed: %s", e)

        messages = (
            [{"role": "system", "content": system_prompt}]
            + history
            + [{"role": "user", "content": processed}]
        )
        token_budget = _TOKEN_BUDGETS.get(query_intent, 512)
        try:
            resp = _client().chat(
                model=selected_model,
                messages=messages,
                options={
                    "temperature": 0.65,
                    "num_predict": token_budget,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                },
            )
            return resp["message"]["content"]
        except Exception as e:
            if "Connection refused" in str(e) or "Errno 61" in str(e):
                logger.error("Ollama not running — run: ollama serve")
                return "⚠️ Ollama is offline. Please run `ollama serve` in a terminal."
            logger.error("ollama.chat failed: %s", e)
            return "I can't reach my model right now."

    def stream(
        self,
        user_input: str,
        system_prompt: str,
        selected_model: str,
        query_intent: str,
        history: List[Dict],
        temperature: float,
        token_budget: int,
    ) -> Generator:
        messages = [{"role": "system", "content": system_prompt}] + history
        full_reply = ""
        buffer = ""
        sentence_re = re.compile(r"([^.!?\n]*[.!?\n]+)")
        # TTS handled by global persistent worker thread

        try:
            for chunk in _client().chat(
                model=selected_model,
                messages=messages,
                stream=True,
                options={"temperature": temperature, "num_predict": token_budget},
            ):
                token = chunk["message"]["content"]
                if not token:
                    continue
                full_reply += token
                buffer += token
                yield {"token": token}
                while True:
                    m = sentence_re.match(buffer)
                    if not m:
                        break
                    sentence = m.group(1).strip()
                    buffer = buffer[m.end() :]
                    if len(sentence) > 4:
                        _tts_q.put(sentence)
            if buffer.strip() and len(buffer.strip()) > 4:
                _tts_q.put(buffer.strip())
        except Exception as e:
            if "Connection refused" in str(e) or "Errno 61" in str(e):
                logger.error("Ollama not running — run: ollama serve")
                yield {"token": "⚠️ Ollama is offline. Please run `ollama serve`."}
            else:
                logger.error("LLMEngine.stream ollama error: %s", e)
                yield {"token": f"Error: {e}"}
        finally:
            pass

        yield {"__full_reply__": full_reply}


def stream_response(
    user_input: str, system_prompt: str = "", model: str = "phi3:mini"
) -> Generator:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_input})
    try:
        for chunk in _client().chat(model=model, messages=messages, stream=True):
            token = chunk["message"]["content"]
            if token:
                yield token
    except Exception as e:
        if "Connection refused" in str(e) or "Errno 61" in str(e):
            logger.error("Ollama not running — run: ollama serve")
            yield "⚠️ Ollama is offline. Please run `ollama serve`."
        else:
            logger.error("stream_response error: %s", e)
            yield f"Error: {e}"
