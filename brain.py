# ==========================================
# core/brain.py - v5.0  REFACTORED
# ==========================================
import logging, re, threading
from typing import Dict, Generator, List, Optional

import ollama

from core.capabilities import CapabilityManager
from core.confidence import score as confidence_score, label as confidence_label
from core.model_manager import ModelManager
from core.truth_guard import TruthGuard
from core.response_cache import ResponseCache
from core.early_exit_handler import EarlyExitHandler
from core.context_builder import ContextBuilder
from core.post_processor import PostProcessor
from core.memory_manager import MemoryManager

from emotion.emotion_detector import detect_emotion
from intents.classifier import is_question_like
from personality.modes import get_token_budget, get_temperature
from utils.cleaner import clean_text
from websearch.search_agent import WebSearchAgent

from tools.tool_router import detect_tool
from tools.file_reader import read_file, extract_filepath, list_files
from tools.system_monitor import get_system_info, analyze_performance
from tools.git_tool import is_git_repo, git_status, git_diff, git_log, git_branch, propose_git_commit
from tools.task_manager import TaskManager
from tools.python_sandbox import propose_python_execution, extract_python_code

logger = logging.getLogger(__name__)

_LOCAL_QUERY_WORDS = {"my project","my code","in the project","my file","my folder","where is","which file","codebase"}
_SEARCH_TRIGGERS   = {"search","google","look up","find out","latest","current","news","today","recent","who is","when did","where is","price of","weather"}
_HARD_STOP = (
    "CRITICAL: 1) Never start with Hey/Hi/Sure/Certainly/Of course. "
    "2) Answer ONLY what was asked. 3) No suggestions unless asked. "
    "4) Stop when done. 5) First word must be content, not filler."
)

def _needs_web_search(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in _SEARCH_TRIGGERS)

def _is_local_query(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _LOCAL_QUERY_WORDS)


class Brain:

    def __init__(self) -> None:
        self.truth_guard   = TruthGuard()
        self.capabilities  = CapabilityManager()
        self.model_manager = ModelManager(default_model="phi3:mini")
        self.search_agent  = WebSearchAgent()
        self._cache = ResponseCache()
        self._exit  = EarlyExitHandler()
        self._ctx   = ContextBuilder()
        self._post  = PostProcessor(self.truth_guard)
        self._mem   = MemoryManager()
        self.conversation_history: List[Dict] = []
        try:
            from memory_db import load_recent_history, init_db
            init_db()
            self.conversation_history = load_recent_history(n=15)
        except Exception as e:
            logger.warning("memory_db init failed: %s", e)
        logger.info("🚀 Brain v5.0 initialized")

    # ── Non-streaming ──────────────────────────────────────────────────────
    def process(self, user_input: str, vision_mode: bool = False) -> Dict:
        try:
            user_input = clean_text(user_input)
            if not user_input:
                return self._error_reply("I didn't catch that. Try again?")

            mode_reply = self._exit.check_mode_switch(user_input)
            if mode_reply:
                return self._build_reply(mode_reply, "neutral", "mode_switch", "system", confidence=1.0)

            if not vision_mode:
                cached = self._cache.get(user_input)
                if cached:
                    return cached

            chain_reply = self._exit.check_chain(user_input, self)
            if chain_reply:
                return {"reply": chain_reply, "emotion": "neutral", "intent": "chain", "agent": "chain_executor", "confidence": 0.9}

            memory = self._mem.load()
            brief  = self._exit.check_briefing(memory)
            if brief:
                return {"reply": brief, "emotion": "neutral", "intent": "briefing", "agent": "briefing", "confidence": 1.0}

            user_name                    = self._mem.user_name(memory)
            emotion_label, emotion_score = detect_emotion(user_input)
            memory                       = self._mem.update_emotion(memory, emotion_label, emotion_score)
            logger.info("emotion | label=%s score=%.2f", emotion_label, emotion_score)
            self.truth_guard.update_user_info(user_name=user_name, user_location=self._mem.user_location(memory))

            qt = self._exit.check_quick_tools(user_input)
            if qt:
                reply, intent, agent = qt
                self._mem.save(memory)
                return self._build_reply(reply, emotion_label, intent, agent, confidence=1.0)

            shortcut = self._exit.check_intent_shortcut(user_input, user_name)
            if shortcut and not vision_mode:
                self._mem.save(memory)
                r = self._build_reply(shortcut, emotion_label, "shortcut", "intent_handler",
                                      confidence=confidence_score("shortcut", "shortcut"))
                self._cache.set(user_input, r)
                return r

            self_reply = self._exit.check_self_query(user_input, user_name)
            if self_reply:
                self._mem.save(memory)
                return self._build_reply(self_reply, emotion_label, "self_awareness", "self", confidence=1.0)

            tool = detect_tool(user_input)
            if tool and self.capabilities.is_enabled(tool):
                tool_resp = self._handle_tool_request(user_input, tool, memory, user_name)
                if tool_resp:
                    self._mem.save(memory)
                    return tool_resp

            fact, memory = self._mem.extract_and_store_fact(user_input, memory, user_name)
            memory_updated = fact is not None
            if fact:
                self._mem.save(memory)
                if not is_question_like(user_input):
                    return self._build_reply(self._mem.acknowledge_fact(fact), emotion_label,
                                             "memory_storage", "memory", memory_updated=True,
                                             confidence=confidence_score("memory_storage", "memory_storage"))

            recalled = self._mem.recall(user_input, memory, user_name)
            if recalled:
                self._mem.save(memory)
                return self._build_reply(recalled, emotion_label, "memory_recall", "memory",
                                         confidence=confidence_score("memory_recall", "memory_recall"))

            if self.capabilities.is_enabled("web_search") and _needs_web_search(user_input) and not _is_local_query(user_input):
                self.search_agent.model = self.model_manager.select_model(user_input, "research")
                result = self.search_agent.run(user_input, user_name)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", result["reply"])
                self._mem.save(memory)
                return self._build_reply(result["reply"], emotion_label, "web_search", "web_search_agent",
                                         tool_used=True, citations=result.get("citations") or [],
                                         results_count=result.get("results_count", 0),
                                         memory_updated=memory_updated,
                                         confidence=confidence_score("web_search_agent", "web_search"))

            query_intent   = self.model_manager.classify_query_intent(user_input)
            selected_model = self.model_manager.select_model(user_input, query_intent)
            logger.info("model | model=%s intent=%s", selected_model, query_intent)

            system_prompt, sem_conf = self._ctx.build(user_input, user_name, memory, emotion_label,
                                                       query_intent, self.conversation_history)
            reply = self._try_react(user_input, selected_model, system_prompt, user_name)
            if not reply:
                reply = self._llm_call(user_input, system_prompt, selected_model, query_intent)
            self._add_to_history("assistant", reply)

            reply = self._post.process(reply, user_input, user_name, memory,
                                       selected_model, query_intent, emotion_label, emotion_score)
            self._mem.post_turn(user_input, reply, memory, user_name, query_intent,
                                emotion_label, self.conversation_history, selected_model)

            final_conf = max(confidence_score(f"ollama/{selected_model}", query_intent), sem_conf)
            result = self._build_reply(reply, emotion_label, query_intent, f"ollama/{selected_model}",
                                       memory_updated=memory_updated, confidence=final_conf)
            self._cache.set(user_input, result)
            return result

        except Exception as e:
            logger.error("Brain.process error: %s", e, exc_info=True)
            return self._error_reply("Something went wrong.")

    # ── Streaming ──────────────────────────────────────────────────────────
    def process_stream(self, user_input: str) -> Generator:
        user_input = clean_text(user_input)
        if not user_input:
            yield {"token": "I didn't catch that — try again?"}
            return

        memory    = self._mem.load()
        user_name = self._mem.user_name(memory)

        mode_reply = self._exit.check_mode_switch(user_input)
        if mode_reply:
            yield {"token": mode_reply}
            return

        cached = self._cache.get(user_input)
        if cached:
            for word in cached.get("reply", "").split(" "):
                yield {"token": word + " "}
            return

        chain_reply = self._exit.check_chain(user_input, self)
        if chain_reply:
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", chain_reply)
            self._mem.save(memory)
            for word in chain_reply.split(" "):
                yield {"token": word + " "}
            return

        emotion_label, emotion_score = detect_emotion(user_input)
        memory = self._mem.update_emotion(memory, emotion_label, emotion_score)

        qt = self._exit.check_quick_tools(user_input)
        if qt:
            reply, _, _ = qt
            self._mem.save(memory)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", reply)
            for word in reply.split(" "):
                yield {"token": word + " "}
            return

        shortcut = self._exit.check_intent_shortcut(user_input, user_name)
        if shortcut:
            self._mem.save(memory)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", shortcut)
            self._cache.set(user_input, {"reply": shortcut})
            for word in shortcut.split(" "):
                yield {"token": word + " "}
            return

        self_reply = self._exit.check_self_query(user_input, user_name)
        if self_reply:
            self._mem.save(memory)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", self_reply)
            for word in self_reply.split(" "):
                yield {"token": word + " "}
            return

        tool = detect_tool(user_input)
        if tool and self.capabilities.is_enabled(tool):
            tool_resp = self._handle_tool_request(user_input, tool, memory, user_name)
            if tool_resp:
                reply = tool_resp.get("reply", "")
                self._mem.save(memory)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", reply)
                for word in reply.split(" "):
                    yield {"token": word + " "}
                return

        fact, memory = self._mem.extract_and_store_fact(user_input, memory, user_name)
        if fact:
            self._mem.save(memory)
            if not is_question_like(user_input):
                ack = self._mem.acknowledge_fact(fact)
                self._add_to_history("user", user_input)
                self._add_to_history("assistant", ack)
                for word in ack.split(" "):
                    yield {"token": word + " "}
                return

        recalled = self._mem.recall(user_input, memory, user_name)
        if recalled:
            self._mem.save(memory)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", recalled)
            for word in recalled.split(" "):
                yield {"token": word + " "}
            return

        if self.capabilities.is_enabled("web_search") and _needs_web_search(user_input) and not _is_local_query(user_input):
            result = self.search_agent.run(user_input, user_name)
            reply  = result.get("reply", "")
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", reply)
            self._mem.save(memory)
            for word in reply.split(" "):
                yield {"token": word + " "}
            return

        query_intent   = self.model_manager.classify_query_intent(user_input)
        selected_model = self.model_manager.select_model(user_input, query_intent)
        temperature    = get_temperature()
        token_budget   = get_token_budget(query_intent)

        system_prompt, sem_conf = self._ctx.build(user_input, user_name, memory, emotion_label,
                                                   query_intent, self.conversation_history)
        self._add_to_history("user", user_input)
        messages    = [{"role": "system", "content": system_prompt}] + self.conversation_history
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
                                     options={"temperature": temperature, "num_predict": token_budget}):
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
            logger.error("process_stream ollama error: %s", e)
            yield {"token": f"Error: {e}"}
        finally:
            tts_done.set()

        full_reply = self._post.process(full_reply, user_input, user_name, memory,
                                        selected_model, query_intent, emotion_label, emotion_score)
        self._add_to_history("assistant", full_reply)
        self._mem.post_turn(user_input, full_reply, memory, user_name, query_intent,
                            emotion_label, self.conversation_history, selected_model)

        final_conf = max(confidence_score(f"ollama/{selected_model}", query_intent), sem_conf)
        yield {"meta": {"full": full_reply, "agent": f"ollama/{selected_model}",
                        "intent": query_intent, "emotion": emotion_label,
                        "confidence": final_conf, "tool_used": False, "memory_updated": True}}

    # ── Tool handler ───────────────────────────────────────────────────────
    def _handle_tool_request(self, user_input, tool, memory, user_name):
        logger.info("tool | tool=%s", tool)

        if tool == "file_reader":
            filepath = extract_filepath(user_input)
            if not filepath:
                if any(w in user_input.lower() for w in ["list", "show files", "what files"]):
                    result = list_files()
                    if result["success"]:
                        files_str = "\n".join(f"{'��' if f['type']=='dir' else '📄'} {f['name']}" for f in result["files"][:20])
                        reply = f"Files in {result['directory']}:\n{files_str}"
                        if result["count"] > 20:
                            reply += f"\n... and {result['count'] - 20} more"
                    else:
                        reply = f"Error: {result['error']}"
                else:
                    reply = "Which file? Try: 'read backend.py'"
                return self._build_reply(reply, "neutral", "file_operation", "file_reader", tool_used=True, confidence=0.95)
            result = read_file(filepath)
            if result["success"]:
                prompt = (f"Analyze this file: 1 sentence description, 3-5 key components, any obvious issues. Under 100 words.\n\n"
                          f"File: {result['filepath']} ({result['lines']} lines)\n\n{result['content'][:3000]}")
                try:
                    resp     = ollama.chat(model=self.model_manager.select_model(user_input, "technical"),
                                           messages=[{"role": "user", "content": prompt}],
                                           options={"temperature": 0.3, "num_predict": 200})
                    analysis = resp["message"]["content"]
                except Exception as e:
                    logger.warning("file analysis LLM failed: %s", e)
                    analysis = f"Read {result['lines']} lines from {filepath}"
                reply = f"📄 {result['filepath']} ({result['lines']} lines)\n\n{analysis}"
                if result.get("truncated"):
                    reply += f"\n\n(First {result['truncated_at']} lines shown)"
            else:
                reply = f"❌ {result['error']}"
            return self._build_reply(reply, "neutral", "file_analysis", "file_reader", tool_used=True, confidence=0.90)

        elif tool == "system_monitor":
            info = get_system_info()
            if "why" in user_input.lower() and "slow" in user_input.lower():
                summary = analyze_performance()
                reply   = f"System Status:\n{summary}\n\nTop Processes:\n"
                for p in info["top_processes"][:3]:
                    reply += f"• {p['name']}: {p['cpu']}% CPU, {p['memory']}% RAM\n"
            elif info["success"]:
                reply = (f"💻 CPU: {info['cpu']['percent']}% | "
                         f"RAM: {info['memory']['used_gb']}/{info['memory']['total_gb']}GB | "
                         f"Disk: {info['disk']['free_gb']}GB free")
            else:
                reply = f"Error: {info['error']}"
            return self._build_reply(reply, "neutral", "system_info", "system_monitor", tool_used=True, confidence=0.95)

        elif tool == "task_manager":
            import re as _re
            tm, text = TaskManager(memory), user_input.lower()
            if any(w in text for w in ["add task", "new task", "remind me", "todo"]):
                m     = _re.search(r'(?:add task|new task|remind me to|todo|task:)\s+(.+)', user_input, _re.IGNORECASE)
                reply = f"✓ {tm.add_task(m.group(1).strip())['message']}" if m else "What task?"
                self._mem.save(memory)
            elif any(w in text for w in ["my tasks", "show tasks", "list tasks"]):
                result = tm.list_tasks()
                if result["count"] == 0:
                    reply = "No tasks! Want to add one?"
                else:
                    reply = f"Tasks ({result['count']}):\n"
                    for t in result["tasks"]:
                        emoji    = "✅" if t["status"] == "done" else "⏳"
                        priority = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t["priority"], "")
                        reply   += f"{emoji}{priority} {t['title']}" + (f" (due: {t['deadline']})" if t["deadline"] else "") + "\n"
            elif any(w in text for w in ["complete", "done", "finish"]):
                result = tm.list_tasks(status="todo")
                if result["count"] > 0:
                    task = result["tasks"][0]
                    tm.complete_task(task["id"])
                    self._mem.save(memory)
                    reply = f"✅ Completed: {task['title']}"
                else:
                    reply = "No pending tasks!"
            else:
                reply = "Task commands: 'add task', 'my tasks', 'complete task'"
            return self._build_reply(reply, "neutral", "task_management", "task_manager",
                                     tool_used=True, confidence=0.95, memory_updated=True)

        elif tool == "git":
            if not is_git_repo():
                return self._build_reply("Not in a git repo.", "neutral", "git_error", "git", confidence=1.0)
            import re as _re
            text = user_input.lower()
            if "status" in text or "what changed" in text:
                result = git_status()
                reply  = ("Clean repo ✓" if result.get("clean") else
                          "Changes:\n" + (f"Modified: {', '.join(result['modified'])}\n" if result.get("modified") else "")
                          + (f"Added: {', '.join(result['added'])}\n" if result.get("added") else "")
                          + (f"Untracked: {', '.join(result['untracked'])}\n" if result.get("untracked") else "")
                          ) if result["success"] else f"Error: {result['error']}"
            elif "log" in text or "commits" in text:
                result = git_log(5)
                reply  = ("Recent commits:\n" + "".join(f"• {c['hash']} {c['message']} ({c['time']})\n"
                          for c in result.get("commits", []))) if result["success"] else f"Error: {result['error']}"
            elif "branch" in text:
                result = git_branch()
                reply  = (f"Branch: {result['current_branch']}\n" + "".join(
                    f"{'*' if b['current'] else ' '} {b['name']}\n" for b in result.get("branches", [])[:10])
                ) if result["success"] else f"Error: {result['error']}"
            elif "commit" in text:
                m        = _re.search(r'commit\s+(.+?)$', user_input, _re.IGNORECASE)
                proposal = propose_git_commit(m.group(1) if m else "Update files")
                if not proposal["success"]:
                    reply = proposal["error"]
                else:
                    return {"reply": "Git commit proposed", "emotion": "neutral", "intent": "git_commit_proposal",
                            "agent": "git", "tool_used": True, "confidence": 1.0,
                            "approval_required": True, "proposal": proposal}
            elif "diff" in text:
                result = git_diff()
                reply  = (f"```\n{result['output'][:1000]}\n```" + ("\n(truncated)" if len(result["output"]) > 1000 else "")
                          ) if result["success"] else f"Error: {result['error']}"
            else:
                reply = "Git: status | log | branch | commit | diff"
            return self._build_reply(reply, "neutral", "git_operation", "git", tool_used=True, confidence=0.90)

        elif tool == "python_sandbox":
            code = extract_python_code(user_input)
            if not code:
                return self._build_reply("No Python code found. Wrap in ```python``` blocks.",
                                         "neutral", "python_error", "python_sandbox", confidence=0.80)
            return {"reply": "Python execution proposed", "emotion": "neutral", "intent": "python_execution_proposal",
                    "agent": "python_sandbox", "tool_used": True, "confidence": 1.0,
                    "approval_required": True, "proposal": propose_python_execution(code)}
        return None

    # ── Private helpers ────────────────────────────────────────────────────
    def _try_react(self, user_input, selected_model, context, user_name) -> str:
        try:
            from agents.react_agent import react, needs_react
            if needs_react(user_input):
                logger.info("⚛️  ReAct triggered")
                reply = react(user_input, model=selected_model, context=context, user_name=user_name)
                if reply and len(reply.split()) >= 10:
                    self._add_to_history("user", user_input)
                    self._add_to_history("assistant", reply)
                    return reply
        except Exception as e:
            logger.warning("react_agent failed: %s", e)
        return ""

    def _llm_call(self, user_input, system_prompt, selected_model, query_intent) -> str:
        try:
            from agents.reasoner import reason
            processed = reason(user_input, model=selected_model)
        except Exception as e:
            logger.warning("reasoner failed: %s", e)
            processed = user_input
        injected     = processed + " (Reply directly, no greeting, no filler.)"
        self._add_to_history("user", injected)
        messages     = [{"role": "system", "content": _HARD_STOP + "\n\n" + system_prompt}] + self.conversation_history
        token_budget = {"coding": 600, "technical": 500, "reasoning": 450, "research": 400}.get(query_intent, 300)
        try:
            resp = ollama.chat(model=selected_model, messages=messages,
                               options={"temperature": 0.65, "num_predict": token_budget, "top_p": 0.9, "repeat_penalty": 1.1})
            return resp["message"]["content"]
        except Exception as e:
            logger.error("ollama.chat failed: %s", e)
            return "I can't reach my model right now."

    def _add_to_history(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})
        if role == "assistant" and len(self.conversation_history) >= 2:
            try:
                from memory_db import save_exchange
                last_user = next((m["content"] for m in reversed(self.conversation_history[:-1]) if m["role"] == "user"), "")
                save_exchange(last_user, content)
            except Exception as e:
                logger.warning("save_exchange failed: %s", e)
        if len(self.conversation_history) > 12:
            self.conversation_history = self.conversation_history[-12:]

    def _build_reply(self, reply, emotion, intent, agent,
                     tool_used=False, memory_updated=False,
                     citations=None, results_count=0, confidence=0.6) -> Dict:
        conf_info = confidence_label(confidence)
        result = {"reply": reply, "emotion": emotion, "intent": intent, "agent": agent,
                  "tool_used": tool_used, "memory_updated": memory_updated,
                  "confidence": confidence, "confidence_label": conf_info["text"], "confidence_emoji": conf_info["emoji"]}
        if citations:
            result["citations"]     = citations
            result["results_count"] = results_count
        return result

    def _error_reply(self, message: str) -> Dict:
        return {"reply": message, "emotion": "neutral", "intent": "error", "agent": "error_handler",
                "tool_used": False, "memory_updated": False, "confidence": 0.0,
                "confidence_label": "UNKNOWN", "confidence_emoji": "⚪"}

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
        logger.error("stream_response error: %s", e)
        yield f"Error: {e}"
