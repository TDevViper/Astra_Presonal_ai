# ==========================================
# core/brain.py - v4.1 FULL PIPELINE STREAM
# ==========================================

import logging
from typing import Dict, List, Optional
import ollama

from emotion.emotion_detector import detect_emotion
from emotion.emotion_memory import update_emotion, ensure_emotion_memory
from emotion.emotion_responder import choose_reply as emotion_reply

from intents.shortcuts import detect_intent
from intents.classifier import is_question_like

from memory.memory_engine import load_memory, save_memory
from memory.memory_extractor import extract_user_fact
from memory.memory_recall import memory_recall
from memory.summarizer import (
    should_summarize, summarize_conversation,
    store_summary, get_recent_context
)
from memory.semantic_recall import (
    build_semantic_context, index_user_fact, index_exchange
)

from core.truth_guard import TruthGuard
from core.capabilities import CapabilityManager
from core.model_manager import ModelManager
from core.confidence import score as confidence_score, label as confidence_label

from agents.reasoner import reason
from agents.critic import critic_review
from reflection.refinement import refine_reply

from websearch.search_agent import WebSearchAgent

from utils.cleaner import clean_text
from personality.modes import (
    detect_mode_switch, set_mode, get_mode_banner,
    get_token_budget, get_temperature, get_model_bias, get_system_addon
)
from memory.episodic import store_episode, build_episodic_context
from core.self_awareness import is_self_query, get_self_response
from core.proactive import get_proactive_suggestion, get_session_summary
from personality.system import build_system_prompt
from utils.polisher import polish_reply
from utils.limiter import limit_words, detect_intent_for_limit

from tools.tool_router import detect_tool
from tools.system_controller import handle_system_command, is_system_command
from tools.calendar_tool import handle_calendar_command, morning_briefing_text, reminder_check_text
from tools.whatsapp_tool import handle_whatsapp_command
from tools.web_search import handle_search_command
from tools.file_reader import read_file, extract_filepath, list_files
from tools.system_monitor import get_system_info, analyze_performance
from tools.git_tool import (
    is_git_repo, git_status, git_diff, git_log,
    git_branch, propose_git_commit
)
from tools.task_manager import TaskManager
from tools.python_sandbox import propose_python_execution, extract_python_code

logger = logging.getLogger(__name__)

SEARCH_TRIGGERS = [
    "search", "google", "look up", "find out", "latest",
    "current", "news", "today", "recent",
    "who is", "when did", "where is", "price of", "weather"
]

import time as _time
from core.cache import get_cached as _get_cached, set_cached as _set_cache


def needs_web_search(text: str) -> bool:
    return any(trigger in text.lower() for trigger in SEARCH_TRIGGERS)


class Brain:

    def __init__(self) -> None:
        self.truth_guard          = TruthGuard()
        self.capabilities         = CapabilityManager()
        self.model_manager        = ModelManager(default_model="phi3:mini")
        self.search_agent         = WebSearchAgent()
        self.conversation_history: List[Dict] = []
        try:
            from memory_db import load_recent_history, init_db
            init_db()
            self.conversation_history = load_recent_history(n=15)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle
        logger.info("🚀 Brain v4.1 initialized")

    def process(self, user_input: str, vision_mode: bool = False) -> Dict:
        try:
            user_input = clean_text(user_input)

            mode_switch = detect_mode_switch(user_input)
            if mode_switch:
                set_mode(mode_switch)
                from personality.modes import get_mode_banner
                return self._build_reply(reply=f'Mode switched: {get_mode_banner()}', emotion='neutral', intent='mode_switch', agent='system', confidence=1.0)

            cached = _get_cached(user_input)
            if cached and not vision_mode:
                return cached

            try:
                from tools.chain_planner import detect_chain, build_chain_plan, execute_chain
                _steps = detect_chain(user_input)
                if _steps:
                    _plan   = build_chain_plan(user_input, _steps)
                    _result = execute_chain(_plan, self)
                    return {"reply": _result, "emotion": "neutral", "intent": "chain",
                            "agent": "chain_executor", "confidence": 0.9, "model": "chain"}
            except Exception:
                pass  # TODO: handle

            try:
                from briefing import should_give_briefing, generate_morning_brief, mark_briefing_done
                _mem = load_memory()
                if should_give_briefing(_mem):
                    _brief = generate_morning_brief(_mem)
                    _mem   = mark_briefing_done(_mem)
                    save_memory(_mem)
                    return {"reply": _brief, "emotion": "neutral", "intent": "briefing",
                            "agent": "briefing", "confidence": 1.0, "model": "briefing"}
            except Exception:
                pass  # TODO: handle

            if not user_input:
                return self._error_reply("I didn't catch that. Try again?")

            memory    = load_memory()
            memory    = ensure_emotion_memory(memory)
            user_name = memory.get("preferences", {}).get("name", "User")
            user_loc  = memory.get("preferences", {}).get("location", "")

            self.truth_guard.update_user_info(user_name=user_name, user_location=user_loc)

            emotion_label, emotion_score = detect_emotion(user_input)
            memory = update_emotion(memory, emotion_label, emotion_score)
            logger.info(f"emotion | label={emotion_label} score={emotion_score:.2f}")

            for handler, intent, agent in [
                (handle_search_command,   "web_search",     "web_search_agent"),
                (handle_whatsapp_command, "whatsapp",       "whatsapp"),
                (handle_calendar_command, "calendar",       "calendar"),
                (handle_system_command,   "system_control", "system_controller"),
            ]:
                result = handler(user_input)
                if result:
                    save_memory(memory)
                    return self._build_reply(reply=result, emotion=emotion_label,
                                             intent=intent, agent=agent, confidence=1.0)

            bye_words = ["bye", "goodbye", "exit", "quit", "see you", "good night", "cya"]
            is_bye    = any(w in user_input.lower() for w in bye_words)

            shortcut = detect_intent(user_input, user_name)
            if shortcut and not vision_mode:
                if is_bye:
                    summary = get_session_summary(user_name)
                    if summary:
                        shortcut = shortcut + "\n\n📊 " + summary
                save_memory(memory)
                r = self._build_reply(reply=shortcut, emotion=emotion_label,
                                      intent="shortcut", agent="intent_handler",
                                      confidence=confidence_score("shortcut", "shortcut"))
                _set_cache(user_input, r)
                return r

            if is_self_query(user_input):
                reply = get_self_response(user_input, user_name)
                save_memory(memory)
                return self._build_reply(reply=reply, emotion=emotion_label,
                                         intent="self_awareness", agent="self", confidence=1.0)

            tool = detect_tool(user_input)
            if tool and self.capabilities.is_enabled(tool):
                tool_response = self._handle_tool_request(user_input, tool, memory, user_name)
                if tool_response:
                    save_memory(memory)
                    return tool_response

            new_fact       = extract_user_fact(user_input)
            memory_updated = False

            if new_fact:
                memory = self._store_fact(new_fact, memory)
                index_user_fact(new_fact, user_name=user_name)
                save_memory(memory)
                memory_updated = True
                if not is_question_like(user_input):
                    return self._build_reply(
                        reply=self._acknowledge_fact(new_fact),
                        emotion=emotion_label, intent="memory_storage",
                        agent="memory", memory_updated=True,
                        confidence=confidence_score("memory_storage", "memory_storage")
                    )

            recalled = memory_recall(user_input, memory, user_name)
            if recalled:
                save_memory(memory)
                return self._build_reply(reply=recalled, emotion=emotion_label,
                                         intent="memory_recall", agent="memory",
                                         confidence=confidence_score("memory_recall", "memory_recall"))

            _local_query = any(w in user_input.lower() for w in [
                "my project", "my code", "in the project", "my file",
                "my folder", "where is", "which file", "codebase"
            ])
            if self.capabilities.is_enabled("web_search") and needs_web_search(user_input) and not _local_query:
                self.search_agent.model = self.model_manager.select_model(user_input, "research")
                result = self.search_agent.run(user_input, user_name)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", result["reply"])
                save_memory(memory)
                return self._build_reply(
                    reply=result["reply"], emotion=emotion_label,
                    intent="web_search", agent="web_search_agent",
                    tool_used=True, citations=result.get("citations") or [],
                    results_count=result.get("results_count", 0),
                    memory_updated=memory_updated,
                    confidence=confidence_score("web_search_agent", "web_search")
                )

            query_intent   = self.model_manager.classify_query_intent(user_input)
            selected_model = self.model_manager.select_model(user_input, query_intent)
            logger.info(f"model | model={selected_model} intent={query_intent}")

            tool_context = ""
            try:
                from core.orchestrator import run_parallel_tools
                parallel_results = run_parallel_tools(user_input)
                if parallel_results:
                    tool_context = "\n".join([
                        f"[{t.upper()}]: {r}"
                        for t, r in parallel_results.items()
                        if r and "error" not in str(r).lower()[:20]
                    ])
            except Exception:
                pass  # TODO: handle

            semantic_ctx, sem_confidence_boost = build_semantic_context(user_input, user_name=user_name)
            try:
                from rag.rag_engine import query_rag, should_use_rag
                if should_use_rag(user_input):
                    rag_ctx = query_rag(user_input, top_k=3)
                    if rag_ctx:
                        semantic_ctx = (semantic_ctx + "\n\nFROM YOUR FILES:\n" + rag_ctx
                                        if semantic_ctx else "FROM YOUR FILES:\n" + rag_ctx)
            except Exception:
                pass  # TODO: handle

            if tool_context:
                semantic_ctx = (semantic_ctx + "\n\nLIVE CONTEXT:\n" + tool_context
                                if semantic_ctx else "LIVE CONTEXT:\n" + tool_context)

            episodic_ctx = build_episodic_context(user_input, user_name)

            from utils.language_detector import detect_language, get_language_instruction
            lang       = detect_language(user_input)
            lang_instr = get_language_instruction(lang)
            context    = build_system_prompt(
                user_name=user_name, memory=memory,
                emotion=emotion_label, intent=query_intent,
                episodic_ctx=episodic_ctx, semantic_ctx=semantic_ctx,
                lang_instruction=lang_instr,
                conversation_history=self.conversation_history
            )

            processed_input = reason(user_input, model=selected_model)

            from agents.react_agent import react, needs_react
            react_reply = ""
            if needs_react(user_input):
                logger.info("⚛️  ReAct triggered")
                react_reply = react(
                    user_input, model=selected_model,
                    context=semantic_ctx, user_name=user_name
                )

            if react_reply and len(react_reply.split()) >= 10:
                reply = react_reply
                self._add_to_history("user", processed_input)
                self._add_to_history("assistant", reply)
            else:
                hard_stop = (
                    "CRITICAL: 1) Never start with Hey/Hi/Sure/Certainly/Of course. "
                    "2) Answer ONLY what was asked. 3) No suggestions unless asked. "
                    "4) Stop when done. 5) First word must be content, not filler."
                )
                full_context = hard_stop + "\n\n" + context
                _injected    = processed_input + " (Reply directly, no greeting, no filler.)"
                self._add_to_history("user", _injected)
                messages = [{"role": "system", "content": full_context}] + self.conversation_history

                token_budget = {"coding": 600, "technical": 500, "reasoning": 450,
                                "research": 400}.get(query_intent, 300)

                try:
                    response = ollama.chat(
                        model=selected_model,
                        messages=messages,
                        options={
                            "temperature": 0.65,
                            "num_predict": token_budget,
                            "top_p": 0.9,
                            "repeat_penalty": 1.1,
                        }
                    )
                    reply = response["message"]["content"]
                except Exception:
                    reply = "I can't reach my model right now."

                self._add_to_history("assistant", reply)

            reply = critic_review(reply, user_name, memory, user_input=user_input, model=selected_model)
            reply = refine_reply(reply, memory, user_name)

            is_valid, violation = self.truth_guard.validate(reply)
            if not is_valid:
                reply = self.truth_guard.get_safe_reply(violation)

            reply = polish_reply(reply)
            reply = limit_words(reply, intent=detect_intent_for_limit(user_input))

            if emotion_score > 0.7 and emotion_label in ["sad", "angry", "anxious", "tired"]:
                emo   = emotion_reply(emotion_label, emotion_score, user_name, memory)
                reply = f"{emo} {reply}"

            index_exchange(user_input, reply, user_name=user_name)
            store_episode(user_input, reply, intent=query_intent,
                          emotion=emotion_label, user_name=user_name)
            try:
                from knowledge.auto_extractor import extract_from_exchange
                extract_from_exchange(user_input, reply, user_name=user_name)
            except Exception:
                pass  # TODO: handle
            try:
                from core.self_improve import log_response as _log_resp
                _log_resp(user_input, reply, 0.75)
            except Exception:
                pass  # TODO: handle

            if should_summarize(self.conversation_history):
                summary = summarize_conversation(
                    self.conversation_history, memory, user_name, model="phi3:mini"
                )
                memory = store_summary(memory, summary)

            save_memory(memory)

            base_conf  = confidence_score(f"ollama/{selected_model}", query_intent)
            final_conf = max(base_conf, sem_confidence_boost)

            suggestion = get_proactive_suggestion(user_input, memory, user_name)
            if suggestion:
                reply = reply + "\n\n" + suggestion

            result = self._build_reply(
                reply=reply, emotion=emotion_label,
                intent=query_intent, agent=f"ollama/{selected_model}",
                memory_updated=memory_updated, confidence=final_conf
            )
            _set_cache(user_input, result)
            return result

        except Exception as e:
            logger.error(f"Brain.process error: {e}", exc_info=True)
            return self._error_reply("Something went wrong.")

    # ==========================================================
    # STREAMING — full pipeline + post-processing
    # ==========================================================

    def process_stream(self, user_input: str):
        """
        Generator — yields {"token": str} dicts while streaming,
        then yields one {"meta": {...}} dict at the end with enriched
        emotion/confidence/agent/intent for the done frame.

        Full pipeline:
          1.  Mode switch
          2.  Response cache
          3.  Chain detection
          4.  Quick tool shortcuts
          5.  Intent shortcuts
          6.  Self-awareness
          7.  Tool routing
          8.  Fact extraction
          9.  Memory recall
          10. Web search
          11. Ollama streaming (mode-aware temperature + token budget)
          12. Post-processing: critic, refine, truth_guard, polish,
              limit_words, emotion prefix, proactive suggestion,
              episode store, summarize, knowledge graph, self-improve
        """
        import re, threading
        user_input = clean_text(user_input)
        if not user_input:
            yield {"token": "I didn't catch that — try again?"}
            return

        memory    = load_memory()
        memory    = ensure_emotion_memory(memory)
        user_name = memory.get("preferences", {}).get("name", "User")

        # ── 1. Mode switch ────────────────────────────────────────────────
        mode_switch = detect_mode_switch(user_input)
        if mode_switch:
            set_mode(mode_switch)
            yield {"token": f"Mode switched: {get_mode_banner()}"}
            return

        # ── 2. Response cache ─────────────────────────────────────────────
        cached = _get_cached(user_input)
        if cached:
            for word in cached.get("reply", "").split(" "):
                yield {"token": word + " "}
            return

        # ── 3. Chain detection ────────────────────────────────────────────
        try:
            from tools.chain_planner import detect_chain, build_chain_plan, execute_chain
            _steps = detect_chain(user_input)
            if _steps:
                _plan   = build_chain_plan(user_input, _steps)
                _result = execute_chain(_plan, self)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", _result)
                save_memory(memory)
                for word in _result.split(" "):
                    yield {"token": word + " "}
                return
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        emotion_label, emotion_score = detect_emotion(user_input)
        memory = update_emotion(memory, emotion_label, emotion_score)

        # ── 4. Quick tool shortcuts ───────────────────────────────────────
        for handler, intent, agent in [
            (handle_search_command,   "web_search",     "web_search_agent"),
            (handle_whatsapp_command, "whatsapp",       "whatsapp"),
            (handle_calendar_command, "calendar",       "calendar"),
            (handle_system_command,   "system_control", "system_controller"),
        ]:
            result = handler(user_input)
            if result:
                save_memory(memory)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", result)
                for word in result.split(" "):
                    yield {"token": word + " "}
                return

        # ── 5. Intent shortcuts ───────────────────────────────────────────
        shortcut = detect_intent(user_input, user_name)
        if shortcut:
            save_memory(memory)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", shortcut)
            _set_cache(user_input, {"reply": shortcut})
            for word in shortcut.split(" "):
                yield {"token": word + " "}
            return

        # ── 6. Self-awareness ─────────────────────────────────────────────
        if is_self_query(user_input):
            reply = get_self_response(user_input, user_name)
            save_memory(memory)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", reply)
            for word in reply.split(" "):
                yield {"token": word + " "}
            return

        # ── 7. Tool routing ───────────────────────────────────────────────
        tool = detect_tool(user_input)
        if tool and self.capabilities.is_enabled(tool):
            tool_response = self._handle_tool_request(user_input, tool, memory, user_name)
            if tool_response:
                reply = tool_response.get("reply", "")
                save_memory(memory)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", reply)
                for word in reply.split(" "):
                    yield {"token": word + " "}
                return

        # ── 8. Fact extraction ────────────────────────────────────────────
        new_fact = extract_user_fact(user_input)
        if new_fact:
            memory = self._store_fact(new_fact, memory)
            index_user_fact(new_fact, user_name=user_name)
            save_memory(memory)
            if not is_question_like(user_input):
                ack = self._acknowledge_fact(new_fact)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", ack)
                for word in ack.split(" "):
                    yield {"token": word + " "}
                return

        # ── 9. Memory recall ──────────────────────────────────────────────
        recalled = memory_recall(user_input, memory, user_name)
        if recalled:
            save_memory(memory)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", recalled)
            for word in recalled.split(" "):
                yield {"token": word + " "}
            return

        # ── 10. Web search ────────────────────────────────────────────────
        _local_query = any(w in user_input.lower() for w in [
            "my project", "my code", "in the project", "my file",
            "my folder", "where is", "which file", "codebase"
        ])
        if self.capabilities.is_enabled("web_search") and needs_web_search(user_input) and not _local_query:
            self.search_agent.model = self.model_manager.select_model(user_input, "research")
            result = self.search_agent.run(user_input, user_name)
            reply  = result.get("reply", "")
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", reply)
            save_memory(memory)
            for word in reply.split(" "):
                yield {"token": word + " "}
            return

        # ── 11. Ollama streaming ──────────────────────────────────────────
        query_intent   = self.model_manager.classify_query_intent(user_input)
        selected_model = self.model_manager.select_model(user_input, query_intent)
        temperature    = get_temperature()
        token_budget   = get_token_budget(query_intent)

        semantic_ctx, _ = build_semantic_context(user_input, user_name=user_name)
        episodic_ctx    = build_episodic_context(user_input, user_name)

        try:
            from rag.rag_engine import query_rag, should_use_rag
            if should_use_rag(user_input):
                rag_ctx = query_rag(user_input, top_k=3)
                if rag_ctx:
                    semantic_ctx = (semantic_ctx + "\n\nFROM YOUR FILES:\n" + rag_ctx
                                    if semantic_ctx else "FROM YOUR FILES:\n" + rag_ctx)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        tool_context = ""
        try:
            from core.orchestrator import run_parallel_tools
            parallel_results = run_parallel_tools(user_input)
            if parallel_results:
                tool_context = "\n".join([
                    f"[{t.upper()}]: {r}"
                    for t, r in parallel_results.items()
                    if r and "error" not in str(r).lower()[:20]
                ])
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        from utils.language_detector import detect_language, get_language_instruction
        system_prompt = build_system_prompt(
            user_name=user_name, memory=memory,
            emotion=emotion_label, intent=query_intent,
            episodic_ctx=episodic_ctx, semantic_ctx=semantic_ctx,
            lang_instruction=get_language_instruction(detect_language(user_input)),
            conversation_history=self.conversation_history
        )
        if tool_context:
            system_prompt += f"\n\nLIVE TOOL DATA:\n{tool_context}"
        system_prompt += get_system_addon()

        self._add_to_history("user", user_input)
        messages = [{"role": "system", "content": system_prompt}] + self.conversation_history

        buffer      = ""
        full_reply  = ""
        sentence_re = re.compile(r'([^.!?\n]*[.!?\n]+)')
        tts_queue: List[str] = []
        tts_lock    = threading.Lock()
        tts_done    = threading.Event()

        def _tts_worker():
            try:
                from tts_kokoro import speak
                while not tts_done.is_set() or tts_queue:
                    sentence = None
                    with tts_lock:
                        if tts_queue:
                            sentence = tts_queue.pop(0)
                    if sentence:
                        speak(sentence)
                    else:
                        _time.sleep(0.05)
            except Exception:
                pass  # TODO: handle

        tts_thread = threading.Thread(target=_tts_worker, daemon=True)
        tts_thread.start()

        try:
            for chunk in ollama.chat(
                model=selected_model, messages=messages,
                stream=True,
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
                        with tts_lock:
                            tts_queue.append(sentence)

            if buffer.strip() and len(buffer.strip()) > 4:
                with tts_lock:
                    tts_queue.append(buffer.strip())

        except Exception as e:
            logger.error(f"process_stream ollama error: {e}")
            yield {"token": f"Error: {e}"}
        finally:
            tts_done.set()

        # ── 12. Post-processing pipeline ──────────────────────────────────
        try:
            full_reply = critic_review(full_reply, user_name, memory,
                                       user_input=user_input, model=selected_model, intent=query_intent)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            full_reply = refine_reply(full_reply, memory, user_name)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            is_valid, violation = self.truth_guard.validate(full_reply)
            if not is_valid:
                full_reply = self.truth_guard.get_safe_reply(violation)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            full_reply = polish_reply(full_reply)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            full_reply = limit_words(full_reply, intent=detect_intent_for_limit(user_input))
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            if emotion_score > 0.7 and emotion_label in ["sad", "angry", "anxious", "tired"]:
                emo        = emotion_reply(emotion_label, emotion_score, user_name, memory)
                full_reply = f"{emo} {full_reply}"
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            suggestion = get_proactive_suggestion(user_input, memory, user_name)
            if suggestion:
                full_reply = full_reply + "\n\n" + suggestion
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        final_conf = 0.75
        try:
            final_conf = confidence_score(f"ollama/{selected_model}", query_intent)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        self._add_to_history("assistant", full_reply)

        try:
            index_exchange(user_input, full_reply, user_name=user_name)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            store_episode(user_input, full_reply, intent=query_intent,
                          emotion=emotion_label, user_name=user_name)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            if should_summarize(self.conversation_history):
                summary = summarize_conversation(
                    self.conversation_history, memory, user_name, model="phi3:mini"
                )
                memory = store_summary(memory, summary)
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        save_memory(memory)

        try:
            threading.Thread(
                target=__import__("knowledge.auto_extractor", fromlist=["extract_from_exchange"]).extract_from_exchange,
                args=(user_input, full_reply),
                kwargs={"user_name": user_name},
                daemon=True
            ).start()
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        try:
            threading.Thread(
                target=__import__("core.self_improve", fromlist=["log_response"]).log_response,
                args=(user_input, full_reply, final_conf),
                daemon=True
            ).start()
        except Exception as _e:
            logger.debug(f"Non-critical failure: {_e}")  # TODO: handle

        yield {
            "meta": {
                "full":           full_reply,
                "agent":          f"ollama/{selected_model}",
                "intent":         query_intent,
                "emotion":        emotion_label,
                "confidence":     final_conf,
                "tool_used":      False,
                "memory_updated": True,
            }
        }

    # ==========================================================
    # TOOL HANDLER
    # ==========================================================

    def _handle_tool_request(self, user_input, tool, memory, user_name):
        logger.info(f"tool | tool={tool}")

        if tool == "file_reader":
            filepath = extract_filepath(user_input)
            if not filepath:
                if any(w in user_input.lower() for w in ["list", "show files", "what files"]):
                    result = list_files()
                    if result["success"]:
                        files_str = "\n".join(
                            [f"{'📁' if f['type']=='dir' else '📄'} {f['name']}"
                             for f in result["files"][:20]]
                        )
                        reply = f"Files in {result['directory']}:\n{files_str}"
                        if result['count'] > 20:
                            reply += f"\n... and {result['count'] - 20} more"
                    else:
                        reply = f"Error: {result['error']}"
                else:
                    reply = "Which file? Try: 'read backend.py'"
                return self._build_reply(reply=reply, emotion="neutral",
                                         intent="file_operation", agent="file_reader",
                                         tool_used=True, confidence=0.95)
            result = read_file(filepath)
            if result["success"]:
                content        = result["content"]
                lines          = result["lines"]
                summary_prompt = (
                    f"Analyze this file: 1 sentence description, 3-5 key components, "
                    f"any obvious issues. Under 100 words.\n\n"
                    f"File: {result['filepath']} ({lines} lines)\n\n{content[:3000]}"
                )
                try:
                    resp     = ollama.chat(
                        model=self.model_manager.select_model(user_input, "technical"),
                        messages=[{"role": "user", "content": summary_prompt}],
                        options={"temperature": 0.3, "num_predict": 200}
                    )
                    analysis = resp["message"]["content"]
                except Exception:
                    analysis = f"Read {lines} lines from {filepath}"
                reply = f"📄 {result['filepath']} ({lines} lines)\n\n{analysis}"
                if result.get("truncated"):
                    reply += f"\n\n(First {result['truncated_at']} lines shown)"
            else:
                reply = f"❌ {result['error']}"
            return self._build_reply(reply=reply, emotion="neutral",
                                     intent="file_analysis", agent="file_reader",
                                     tool_used=True, confidence=0.90)

        elif tool == "system_monitor":
            info = get_system_info()
            if "why" in user_input.lower() and "slow" in user_input.lower():
                summary = analyze_performance()
                reply   = f"System Status:\n{summary}\n\nTop Processes:\n"
                for p in info["top_processes"][:3]:
                    reply += f"• {p['name']}: {p['cpu']}% CPU, {p['memory']}% RAM\n"
            elif info["success"]:
                reply = (
                    f"💻 CPU: {info['cpu']['percent']}% | "
                    f"RAM: {info['memory']['used_gb']}/{info['memory']['total_gb']}GB | "
                    f"Disk: {info['disk']['free_gb']}GB free"
                )
            else:
                reply = f"Error: {info['error']}"
            return self._build_reply(reply=reply, emotion="neutral",
                                     intent="system_info", agent="system_monitor",
                                     tool_used=True, confidence=0.95)

        elif tool == "task_manager":
            import re
            tm   = TaskManager(memory)
            text = user_input.lower()
            if any(w in text for w in ["add task", "new task", "remind me", "todo"]):
                m = re.search(r'(?:add task|new task|remind me to|todo|task:)\s+(.+)',
                              user_input, re.IGNORECASE)
                reply = f"✓ {tm.add_task(m.group(1).strip())['message']}" if m else "What task?"
                save_memory(memory)
            elif any(w in text for w in ["my tasks", "show tasks", "list tasks"]):
                result = tm.list_tasks()
                if result["count"] == 0:
                    reply = "No tasks! Want to add one?"
                else:
                    reply = f"Tasks ({result['count']}):\n"
                    for t in result["tasks"]:
                        emoji    = "✅" if t["status"] == "done" else "⏳"
                        priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t["priority"], "")
                        reply   += f"{emoji}{priority} {t['title']}"
                        if t["deadline"]:
                            reply += f" (due: {t['deadline']})"
                        reply += "\n"
            elif any(w in text for w in ["complete", "done", "finish"]):
                result = tm.list_tasks(status="todo")
                if result["count"] > 0:
                    task = result["tasks"][0]
                    tm.complete_task(task["id"])
                    save_memory(memory)
                    reply = f"✅ Completed: {task['title']}"
                else:
                    reply = "No pending tasks!"
            else:
                reply = "Task commands: 'add task', 'my tasks', 'complete task'"
            return self._build_reply(reply=reply, emotion="neutral",
                                     intent="task_management", agent="task_manager",
                                     tool_used=True, confidence=0.95, memory_updated=True)

        elif tool == "git":
            if not is_git_repo():
                return self._build_reply(reply="Not in a git repo.", emotion="neutral",
                                         intent="git_error", agent="git", confidence=1.0)
            import re
            text = user_input.lower()
            if "status" in text or "what changed" in text:
                result = git_status()
                if result["success"]:
                    reply = "Clean repo ✓" if result["clean"] else (
                        "Changes:\n" +
                        (f"Modified: {', '.join(result['modified'])}\n" if result["modified"] else "") +
                        (f"Added: {', '.join(result['added'])}\n" if result["added"] else "") +
                        (f"Untracked: {', '.join(result['untracked'])}\n" if result["untracked"] else "")
                    )
                else:
                    reply = f"Error: {result['error']}"
            elif "log" in text or "commits" in text:
                result = git_log(5)
                reply  = "Recent commits:\n" + "".join(
                    f"• {c['hash']} {c['message']} ({c['time']})\n"
                    for c in result.get("commits", [])
                ) if result["success"] else f"Error: {result['error']}"
            elif "branch" in text:
                result = git_branch()
                reply  = (
                    f"Branch: {result['current_branch']}\n" +
                    "".join(f"{'*' if b['current'] else ' '} {b['name']}\n"
                            for b in result.get("branches", [])[:10])
                ) if result["success"] else f"Error: {result['error']}"
            elif "commit" in text:
                m        = re.search(r'commit\s+(.+?)$', user_input, re.IGNORECASE)
                message  = m.group(1) if m else "Update files"
                proposal = propose_git_commit(message)
                if not proposal["success"]:
                    reply = proposal["error"]
                else:
                    return {"reply": "Git commit proposed", "emotion": "neutral",
                            "intent": "git_commit_proposal", "agent": "git",
                            "tool_used": True, "confidence": 1.0,
                            "approval_required": True, "proposal": proposal}
            elif "diff" in text:
                result = git_diff()
                reply  = (
                    f"```\n{result['output'][:1000]}\n```" +
                    ("\n(truncated)" if len(result["output"]) > 1000 else "")
                ) if result["success"] else f"Error: {result['error']}"
            else:
                reply = "Git: status | log | branch | commit | diff"
            return self._build_reply(reply=reply, emotion="neutral",
                                     intent="git_operation", agent="git",
                                     tool_used=True, confidence=0.90)

        elif tool == "python_sandbox":
            code = extract_python_code(user_input)
            if not code:
                return self._build_reply(
                    reply="No Python code found. Wrap in ```python``` blocks.",
                    emotion="neutral", intent="python_error",
                    agent="python_sandbox", confidence=0.80)
            proposal = propose_python_execution(code)
            return {"reply": "Python execution proposed", "emotion": "neutral",
                    "intent": "python_execution_proposal", "agent": "python_sandbox",
                    "tool_used": True, "confidence": 1.0,
                    "approval_required": True, "proposal": proposal}

        return None

    # ==========================================================
    # HELPERS
    # ==========================================================

    def _add_to_history(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})
        if role == "assistant" and len(self.conversation_history) >= 2:
            try:
                from memory_db import save_exchange
                last_user = next((m["content"] for m in reversed(self.conversation_history[:-1])
                                  if m["role"] == "user"), "")
                save_exchange(last_user, content)
            except Exception:
                pass  # TODO: handle
        if len(self.conversation_history) > 12:
            self.conversation_history = self.conversation_history[-12:]

    def _store_fact(self, fact: Dict, memory: Dict) -> Dict:
        memory["user_facts"].append(fact)
        ftype, subtype, value = fact["type"], fact.get("subtype", ""), fact.get("value")
        if ftype == "identity":
            memory["preferences"]["name"] = value
        elif ftype == "location":
            memory["preferences"]["location"] = value
        elif ftype == "preference":
            memory["preferences"][subtype] = value
        return memory

    def _acknowledge_fact(self, fact: Dict) -> str:
        return f"Got it. {fact['fact']}."

    def _build_reply(self, reply, emotion, intent, agent,
                     tool_used=False, memory_updated=False,
                     citations=None, results_count=0, confidence=0.6) -> Dict:
        conf_info = confidence_label(confidence)
        result = {
            "reply":            reply,
            "emotion":          emotion,
            "intent":           intent,
            "agent":            agent,
            "tool_used":        tool_used,
            "memory_updated":   memory_updated,
            "confidence":       confidence,
            "confidence_label": conf_info["text"],
            "confidence_emoji": conf_info["emoji"],
        }
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


brain = Brain()


def stream_response(user_input: str, system_prompt: str = "", model: str = "phi3:mini"):
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
        yield f"Error: {e}"
