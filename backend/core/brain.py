# ==========================================
# core/brain.py - v5.1  SLIM ORCHESTRATOR
# ==========================================
import logging
from typing import Dict, Generator, List, Optional

from core.capabilities import CapabilityManager
from core.confidence import score as confidence_score, label as confidence_label
from core.model_manager import ModelManager
from core.truth_guard import TruthGuard
from core.response_cache import ResponseCache
from core.early_exit_handler import EarlyExitHandler
from core.context_builder import ContextBuilder
from core.post_processor import PostProcessor
from core.memory_manager import MemoryManager
from core.tool_executor import ToolExecutor
from core.llm_engine import LLMEngine, stream_response  # noqa: F401 (re-exported)

from emotion.emotion_detector import detect_emotion
from intents.classifier import is_question_like
from personality.modes import get_token_budget, get_temperature
from utils.cleaner import clean_text
from core.event_bus import publish as _publish
from utils.telemetry import start_span
from core.observability import RequestTrace, get_store as _obs_store
from config import config
from websearch.search_agent import WebSearchAgent
from tools.tool_router import detect_tool, detect_compound

logger = logging.getLogger(__name__)
from core.request_trace import new_trace, step as _step, finish as _finish

_LOCAL_QUERY_WORDS = {"my project","my code","in the project","my file","my folder","where is","which file","codebase"}
import re as _re
_SEARCH_PATTERN = _re.compile(
    r'\b(search for|google|look up|find out|latest|current (price|status|version)|'
    r'news today|what.s happening|who is (the )?ceo|who (won|leads|runs)|'
    r'weather (in|today|tomorrow)|price of|stock price|breaking news)\b',
    _re.IGNORECASE
)


def _sanitize_input(text: str) -> str:
    """Block prompt injection attempts."""
    import re
    injection_patterns = [
        r'(?i)ignore (all )?(previous|above|prior) instructions',
        r'(?i)you are now',
        r'(?i)new (persona|personality|role|instructions)',
        r'(?i)act as (if )?you',
        r'(?i)disregard your',
        r'(?i)\*\*.*instructions.*\*\*',
        r'(?i)system prompt',
        r'(?i)jailbreak',
    ]
    for pattern in injection_patterns:
        if re.search(pattern, text):
            return "[blocked: prompt injection detected]"
    return text

def _needs_web_search(text: str) -> bool:
    return bool(_SEARCH_PATTERN.search(text))

def _is_local_query(text: str) -> bool:
    return any(w in text.lower() for w in _LOCAL_QUERY_WORDS)


class Brain:

    def __init__(self) -> None:
        self.truth_guard   = TruthGuard()
        self.capabilities  = CapabilityManager()
        self.model_manager = ModelManager(default_model=config.DEFAULT_MODEL)
        self.search_agent  = WebSearchAgent()
        self._cache  = ResponseCache()
        self._exit   = EarlyExitHandler()
        self._ctx    = ContextBuilder()
        self._post   = PostProcessor(self.truth_guard)
        self._mem    = MemoryManager()
        self._tools  = ToolExecutor(self.model_manager, self._build_reply)
        self._llm    = LLMEngine(self.model_manager)
        # conversation_history is NOT stored here — it is per-request
        # Use brain_singleton.load_request_history() to get a fresh snapshot
        try:
            from memory_db import init_db
            init_db()
        except Exception as e:
            logger.warning("memory_db init failed: %s", e)
        logger.info("🚀 Brain v5.1 initialized")

    # ── Main entry point ──────────────────────────────────────────────────

    def process(self, user_input: str, vision_mode: bool = False, history: list = None) -> Dict:
        try:
            _trace_id = new_trace(user_input)
            import uuid as _uuid
            _obs = RequestTrace(_uuid.uuid4().hex[:8], user_input)
            _publish("request_start", {"input": user_input[:80]})
            user_input = clean_text(user_input)
            user_input = _sanitize_input(user_input)
            if not user_input:
                return self._error_reply("I didn't catch that. Try again?")

            mode_reply = self._exit.check_mode_switch(user_input)
            if mode_reply:
                return self._build_reply(mode_reply, "neutral", "mode_switch", "system", confidence=1.0)

            if not vision_mode:
                cached = self._cache.get(user_input)
                if cached:
                    _step('cache_hit')
                    return cached

            chain_reply = self._exit.check_chain(user_input, self)
            if chain_reply:
                return {"reply": chain_reply, "emotion": "neutral", "intent": "chain",
                        "agent": "chain_executor", "confidence": 0.9,
                        "tool_used": False, "memory_updated": False,
                        "confidence_label": "HIGH", "confidence_emoji": "🟢"}

            memory = self._mem.load()
            brief  = self._exit.check_briefing(memory)
            if brief:
                return {"reply": brief, "emotion": "neutral", "intent": "briefing",
                        "agent": "briefing", "confidence": 1.0,
                        "tool_used": False, "memory_updated": False,
                        "confidence_label": "HIGH", "confidence_emoji": "🟢"}

            user_name = self._mem.user_name(memory)
            _obs.step_start("llm")
            _publish("llm_start", {"model": self.model_manager.default_model})
            with start_span("brain.resolve", {"intent": "pending", "vision": str(vision_mode)}):
                _history = history if history is not None else []
            result = self._resolve(user_input, memory, user_name, vision_mode=vision_mode, history=_history)
            _obs.step_end("llm", meta=result.get("agent", ""))
            _publish("llm_done", {"reply_len": len(result.get("reply", ""))})
            _finish(intent=result.get("intent", ""), agent=result.get("agent", ""))
            _obs_store().add(_obs.finish(intent=result.get("intent", ""), agent=result.get("agent", "")))
            _publish("response_done", {"intent": result.get("intent"), "ms": _obs.to_dict()["elapsed_ms"]})
            return result

        except Exception as e:
            logger.error("Brain.process error: %s", e, exc_info=True)
            try:
                _obs_store().add(_obs.finish(intent="error", agent="error"))
            except Exception:
                pass
            return self._error_reply("Something went wrong.")

    # ── Shared dispatch — used by both process() and process_stream() ─────

    def _resolve(self, user_input: str, memory: dict, user_name: str,
                 vision_mode: bool = False, history: list = None,
                 streaming: bool = False) -> Dict:
        """
        Run the full dispatch pipeline and return a result dict.
        Returns dict with key 'reply' always set.
        Called by both process() (returns dict) and process_stream() (tokenises reply).
        """
        emotion_label, emotion_score = detect_emotion(user_input)
        memory = self._mem.update_emotion(memory, emotion_label, emotion_score)
        self.truth_guard.update_user_info(
            user_name=user_name,
            user_location=self._mem.user_location(memory)
        )

        # Quick tools
        qt = self._exit.check_quick_tools(user_input)
        if qt:
            reply, intent, agent = qt
            self._mem.save(memory)
            return self._build_reply(reply, emotion_label, intent, agent, confidence=1.0)

        # Intent shortcut
        shortcut = self._exit.check_intent_shortcut(user_input, user_name)
        if shortcut and not vision_mode:
            self._mem.save(memory)
            r = self._build_reply(shortcut, emotion_label, "shortcut", "intent_handler",
                                  confidence=confidence_score("shortcut", "shortcut"))
            self._cache.set(user_input, r)
            return r

        # Self query
        self_reply = self._exit.check_self_query(user_input, user_name)
        if self_reply:
            self._mem.save(memory)
            return self._build_reply(self_reply, emotion_label, "self_awareness", "self", confidence=1.0)

        # Tool dispatch
        compound = detect_compound(user_input)
        if compound:
            return {"reply": compound, "agent": "system_controller", "intent": "shortcut",
                    "emotion": emotion_label, "tool_used": True, "memory_updated": False,
                    "confidence": 1.0, "confidence_label": "HIGH", "confidence_emoji": "🟢"}
        tool = detect_tool(user_input)
        if tool and self.capabilities.is_enabled(tool):
            tool_resp = self._tools.execute(tool, user_input, memory, user_name)
            if tool_resp:
                self._mem.save(memory)
                return tool_resp

        # Fact extraction
        fact, memory = self._mem.extract_and_store_fact(user_input, memory, user_name)
        memory_updated = fact is not None
        if fact:
            self._mem.save(memory)
            if not is_question_like(user_input):
                return self._build_reply(
                    self._mem.acknowledge_fact(fact), emotion_label,
                    "memory_storage", "memory", memory_updated=True,
                    confidence=confidence_score("memory_storage", "memory_storage")
                )

        # Memory recall
        recalled = self._mem.recall(user_input, memory, user_name)
        if recalled:
            self._mem.save(memory)
            return self._build_reply(recalled, emotion_label, "memory_recall", "memory",
                                     confidence=confidence_score("memory_recall", "memory_recall"))

        # Web search
        if (self.capabilities.is_enabled("web_search")
                and _needs_web_search(user_input)
                and not _is_local_query(user_input)):
            self.search_agent.model = self.model_manager.select_model(user_input, "research")
            _search_query = user_input
            for _trigger in ["search for ", "search ", "google ", "look up ", "find "]:
                if _search_query.lower().startswith(_trigger):
                    _search_query = _search_query[len(_trigger):].strip()
                    break
            result = self.search_agent.run(_search_query, user_name)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", result["reply"])
            self._mem.save(memory)
            return self._build_reply(
                result["reply"], emotion_label, "web_search", "web_search_agent",
                tool_used=True, citations=result.get("citations") or [],
                results_count=result.get("results_count", 0),
                memory_updated=memory_updated,
                confidence=confidence_score("web_search_agent", "web_search")
            )

        # LLM path
        query_intent   = self.model_manager.classify_query_intent(user_input)
        selected_model = self.model_manager.select_model(user_input, query_intent)
        system_prompt, sem_conf = self._ctx.build(
            user_input, user_name, memory, emotion_label,
            query_intent, history or []
        )
        try:
            from rag.rag_engine import query_rag, should_use_rag
            if should_use_rag(user_input):
                rag_ctx = query_rag(user_input, top_k=3)
                if rag_ctx:
                    system_prompt += f"\n\nRELEVANT KNOWLEDGE:\n{rag_ctx}"
        except Exception as _e:
            logger.debug('brain: %s', _e)

        self._add_to_history("user", user_input)
        reply = self._llm.try_react(user_input, selected_model, system_prompt, user_name)
        if not reply:
            reply = self._llm.call(user_input, system_prompt, selected_model,
                                   query_intent, history or [])
        self._add_to_history("assistant", reply)

        reply = self._post.process(reply, user_input, user_name, memory,
                                   selected_model, query_intent, emotion_label, emotion_score)
        self._mem.post_turn(user_input, reply, memory, user_name, query_intent,
                            emotion_label, history or [], selected_model)

        final_conf = max(confidence_score(f"ollama/{selected_model}", query_intent), sem_conf)
        result = self._build_reply(reply, emotion_label, query_intent,
                                   f"ollama/{selected_model}",
                                   memory_updated=memory_updated, confidence=final_conf)
        self._cache.set(user_input, result)
        try:
            from core.self_improve import log_response as _si_log
            _si_log(user_input, reply, final_conf)
        except Exception as _e:
            logger.debug('brain: %s', _e)
        return result

    # ── Streaming ─────────────────────────────────────────────────────────

    def process_stream(self, user_input: str, history: list = None) -> Generator:
        user_input = clean_text(user_input)
        user_input = _sanitize_input(user_input)
        if not user_input or user_input.startswith("[blocked"):
            yield {"token": "I didn't catch that — try again?"}
            return

        memory    = self._mem.load()
        user_name = self._mem.user_name(memory)

        # Early exits that don't need _resolve
        mode_reply = self._exit.check_mode_switch(user_input)
        if mode_reply:
            self._mem.save(memory)
            for word in mode_reply.split(" "): yield {"token": word + " "}
            return

        cached = self._cache.get(user_input)
        if cached:
            for word in cached.get("reply", "").split(" "): yield {"token": word + " "}
            return

        chain_reply = self._exit.check_chain(user_input, self)
        if chain_reply:
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", chain_reply)
            self._mem.save(memory)
            for word in chain_reply.split(" "): yield {"token": word + " "}
            return

        # Shared dispatch — reuse _resolve for all remaining logic
        # For LLM path we stream directly; for everything else tokenise the reply
        from personality.modes import get_temperature, get_token_budget
        query_intent   = self.model_manager.classify_query_intent(user_input)
        selected_model = self.model_manager.select_model(user_input, query_intent)

        emotion_label, emotion_score = detect_emotion(user_input)
        memory = self._mem.update_emotion(memory, emotion_label, emotion_score)

        # Try _resolve first (handles tools, memory, web search, shortcuts)
        result = self._resolve(user_input, memory, user_name, history=history or [], streaming=True)
        reply  = result.get("reply", "")

        # If _resolve went to LLM, re-stream it instead of word-splitting
        if result.get("agent", "").startswith("ollama/"):
            system_prompt, sem_conf = self._ctx.build(
                user_input, user_name, memory, emotion_label,
                query_intent, history or []
            )
            self._add_to_history("user", user_input)
            full_reply = ""
            for item in self._llm.stream(
                user_input, system_prompt, selected_model, query_intent,
                history or [], get_temperature(), get_token_budget(query_intent)
            ):
                if "token" in item:
                    full_reply += item["token"]
                    yield item
                elif "__full_reply__" in item:
                    full_reply = item["__full_reply__"]
            self._add_to_history("assistant", full_reply)
            final_conf = result.get("confidence", 0.6)
            yield {"meta": {"full": full_reply, "agent": f"ollama/{selected_model}",
                            "intent": query_intent, "emotion": emotion_label,
                            "confidence": final_conf, "tool_used": False, "memory_updated": True}}
            return

        # Non-LLM result — word-tokenise for streaming consistency
        self._add_to_history("user", user_input)
        self._add_to_history("assistant", reply)
        for word in reply.split(" "): yield {"token": word + " "}
    # ── Helpers ───────────────────────────────────────────────────────────

    def _add_to_history(self, role: str, content: str, history: list = None) -> None:
        """Append to the per-request history list. Never touches shared state."""
        if history is not None:
            history.append({"role": role, "content": content})
        if role == "assistant" and history and len(history) >= 2:
            try:
                from memory_db import save_exchange
                last_user = next((m["content"] for m in reversed(history[:-1])
                                  if m["role"] == "user"), "")
                save_exchange(last_user, content)
            except Exception as e:
                logger.warning("save_exchange failed: %s", e)
            try:
                from memory.summarizer import should_summarize, summarize_conversation, store_summary
                if len(history) > 12 and should_summarize(history):
                    _mem = self._mem.load()
                    _user = self._mem.user_name(_mem)
                    _summary = summarize_conversation(history, _mem, _user)
                    if _summary:
                        _mem = store_summary(_mem, _summary)
                        self._mem.save(_mem)
            except Exception as _e:
                logger.debug('brain summarizer: %s', _e)
            # Trim in-place so callers see the trimmed list
            if len(history) > 12:
                del history[:-12]

    def _build_reply(self, reply, emotion, intent, agent,
                     tool_used=False, memory_updated=False,
                     citations=None, results_count=0, confidence=0.6) -> Dict:
        conf_info = confidence_label(confidence)
        result = {"reply": reply, "emotion": emotion, "intent": intent, "agent": agent,
                  "tool_used": tool_used, "memory_updated": memory_updated,
                  "confidence": confidence, "confidence_label": conf_info["text"],
                  "confidence_emoji": conf_info["emoji"]}
        if citations:
            result["citations"]     = citations
            result["results_count"] = results_count
        return result

    def _error_reply(self, message: str) -> Dict:
        return {"reply": message, "emotion": "neutral", "intent": "error",
                "agent": "error_handler", "tool_used": False, "memory_updated": False,
                "confidence": 0.0, "confidence_label": "UNKNOWN", "confidence_emoji": "⚪"}

    def get_model_info(self) -> Dict:
        return self.model_manager.get_model_info()
