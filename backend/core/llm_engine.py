import logging, re, os, threading
from typing import Generator, List, Dict
import ollama

logger = logging.getLogger(__name__)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def _client():
    return ollama.Client(host=OLLAMA_HOST)

_HARD_STOP = (
    "CRITICAL RULES — follow exactly: "
    "1) Answer ONLY what was asked. No additions, no suggestions, no examples unless asked. "
    "2) Never say: sure/certainly/of course/as an AI/as an artificial intelligence. "
    "3) If you do not know something, say so in one sentence. Do not invent facts. "
    "4) Stop the moment you have answered. No follow-up offers."
)

_TOKEN_BUDGETS = {"coding": 600, "technical": 500, "reasoning": 450, "research": 400}

# ── Global TTS worker (single persistent thread) ──
import queue as _queue
_tts_q = _queue.Queue()

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

import threading as _thr
_thr.Thread(target=_global_tts_worker, daemon=True).start()


class LLMEngine:

    def __init__(self, model_manager):
        self._mm = model_manager

    def try_react(self, user_input: str, selected_model: str,
                  context: str, user_name: str) -> str:
        try:
            from agents.react_agent import react, needs_react
            if needs_react(user_input):
                logger.info("⚛️  ReAct triggered")
                reply = react(user_input, model=selected_model,
                              context=context, user_name=user_name)
                if reply and len(reply.split()) >= 10:
                    return reply
        except Exception as e:
            logger.warning("react_agent failed: %s", e)
        return ""

    def call(self, user_input: str, system_prompt: str,
             selected_model: str, query_intent: str,
             history: List[Dict]) -> str:
        # Only run reasoner on intents that benefit from it
        processed = user_input
        if query_intent in ("reasoning", "technical", "coding", "analysis"):
            try:
                from agents.reasoner import reason
                processed = reason(user_input, model=selected_model)
            except Exception as e:
                logger.warning("reasoner failed: %s", e)

        messages     = ([{"role": "system", "content": _HARD_STOP + "\n\n" + system_prompt}]
                        + history
                        + [{"role": "user", "content": processed}])
        token_budget = _TOKEN_BUDGETS.get(query_intent, 300)
        try:
            resp = _client().chat(
                model=selected_model,
                messages=messages,
                options={"temperature": 0.65, "num_predict": token_budget,
                         "top_p": 0.9, "repeat_penalty": 1.1}
            )
            return resp["message"]["content"]
        except Exception as e:
            if "Connection refused" in str(e) or "Errno 61" in str(e):
                logger.error("Ollama not running — run: ollama serve")
                return "⚠️ Ollama is offline. Please run `ollama serve` in a terminal."
            logger.error("ollama.chat failed: %s", e)
            return "I can't reach my model right now."

    def stream(self, user_input: str, system_prompt: str,
               selected_model: str, query_intent: str,
               history: List[Dict], temperature: float,
               token_budget: int) -> Generator:
        messages    = [{"role": "system", "content": system_prompt}] + history
        full_reply  = ""
        buffer      = ""
        sentence_re = re.compile(r'([^.!?\n]*[.!?\n]+)')
        # TTS handled by global persistent worker thread

        try:
            for chunk in _client().chat(
                model=selected_model, messages=messages, stream=True,
                options={"temperature": temperature, "num_predict": token_budget}
            ):
                token = chunk["message"]["content"]
                if not token:
                    continue
                full_reply += token
                buffer     += token
                yield {"token": token}
                while True:
                    m = sentence_re.match(buffer)
                    if not m:
                        break
                    sentence = m.group(1).strip()
                    buffer   = buffer[m.end():]
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


def stream_response(user_input: str, system_prompt: str = "",
                    model: str = "phi3:mini") -> Generator:
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
