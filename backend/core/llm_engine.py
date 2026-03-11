# core/llm_engine.py
# LLM call logic extracted from Brain — _try_react, _llm_call, stream_response
import logging, re, threading
from typing import Generator, List, Dict

import ollama

logger = logging.getLogger(__name__)

_HARD_STOP = (
    "CRITICAL: 1) Never start with Hey/Hi/Sure/Certainly/Of course. "
    "2) Answer ONLY what was asked. 3) No suggestions unless asked. "
    "4) Stop when done. 5) First word must be content, not filler."
)

_TOKEN_BUDGETS = {"coding": 600, "technical": 500, "reasoning": 450, "research": 400}


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
        try:
            from agents.reasoner import reason
            processed = reason(user_input, model=selected_model)
        except Exception as e:
            logger.warning("reasoner failed: %s", e)
            processed = user_input

        injected     = processed + " (Reply directly, no greeting, no filler.)"
        messages     = ([{"role": "system", "content": _HARD_STOP + "\n\n" + system_prompt}]
                        + history
                        + [{"role": "user", "content": injected}])
        token_budget = _TOKEN_BUDGETS.get(query_intent, 300)
        try:
            resp = ollama.chat(
                model=selected_model,
                messages=messages,
                options={"temperature": 0.65, "num_predict": token_budget,
                         "top_p": 0.9, "repeat_penalty": 1.1}
            )
            return resp["message"]["content"]
        except Exception as e:
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
        tts_queue: list = []
        tts_lock  = threading.Lock()
        tts_done  = threading.Event()

        def _tts_worker():
            try:
                from tts_kokoro import speak
                import time as t
                while not tts_done.is_set() or tts_queue:
                    with tts_lock:
                        sentence = tts_queue.pop(0) if tts_queue else None
                    if sentence:
                        speak(sentence)
                    else:
                        t.sleep(0.05)
            except Exception as e:
                logger.warning("TTS worker error: %s", e)

        threading.Thread(target=_tts_worker, daemon=True).start()

        try:
            for chunk in ollama.chat(model=selected_model, messages=messages, stream=True,
                                     options={"temperature": temperature,
                                              "num_predict": token_budget}):
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
                        with tts_lock:
                            tts_queue.append(sentence)
            if buffer.strip() and len(buffer.strip()) > 4:
                with tts_lock:
                    tts_queue.append(buffer.strip())
        except Exception as e:
            logger.error("LLMEngine.stream ollama error: %s", e)
            yield {"token": f"Error: {e}"}
        finally:
            tts_done.set()

        yield {"__full_reply__": full_reply}


def stream_response(user_input: str, system_prompt: str = "",
                    model: str = "phi3:mini") -> Generator:
    """Standalone streaming helper used by app.py."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_input})
    try:
        for chunk in ollama.chat(model=model, messages=messages, stream=True):
            token = chunk["message"]["content"]
            if token:
                yield token
    except Exception as e:
        logger.error("stream_response error: %s", e)
        yield f"Error: {e}"
