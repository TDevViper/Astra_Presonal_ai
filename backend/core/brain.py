# ==========================================
# core/brain.py - v3.2
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
    should_summarize,
    summarize_conversation,
    store_summary,
    get_recent_context
)
from memory.semantic_recall import (
    build_semantic_context,
    index_user_fact,
    index_exchange
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
from memory.episodic import store_episode, build_episodic_context
from core.self_awareness import is_self_query, get_self_response
from personality.system import build_system_prompt
from utils.polisher import polish_reply
from utils.limiter import limit_words

from tools.tool_router import detect_tool
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


def needs_web_search(text: str) -> bool:
    return any(trigger in text.lower() for trigger in SEARCH_TRIGGERS)


class Brain:

    def __init__(self) -> None:
        self.truth_guard          = TruthGuard()
        self.capabilities         = CapabilityManager()
        self.model_manager        = ModelManager(default_model="phi3:mini")
        self.search_agent         = WebSearchAgent()
        self.conversation_history: List[Dict] = []
        logger.info("🚀 Brain v3.2 initialized")

    # ==========================================================
    # MAIN PIPELINE
    # ==========================================================

    def process(self, user_input: str, vision_mode: bool = False) -> Dict:
        try:
            user_input = clean_text(user_input)
            if not user_input:
                return self._error_reply("I didn't catch that. Try again?")

            memory    = load_memory()
            memory    = ensure_emotion_memory(memory)
            user_name = memory.get("preferences", {}).get("name", "Arnav")
            user_loc  = memory.get("preferences", {}).get("location", "")

            # Keep TruthGuard in sync with latest user info
            self.truth_guard.update_user_info(user_name=user_name, user_location=user_loc)

            # ── 1. Emotion ────────────────────────────────────
            emotion_label, emotion_score = detect_emotion(user_input)
            memory = update_emotion(memory, emotion_label, emotion_score)
            logger.info(f"emotion_detected | label={emotion_label} score={emotion_score:.2f}")

            # ── 2. Shortcuts ──────────────────────────────────
            shortcut = detect_intent(user_input, user_name)
            if shortcut and not vision_mode:
                save_memory(memory)
                return self._build_reply(
                    reply=shortcut, emotion=emotion_label,
                    intent="shortcut", agent="intent_handler",
                    confidence=confidence_score("shortcut", "shortcut")
                )

            # ── 2.1 Self-awareness ────────────────────────────
            if is_self_query(user_input):
                reply = get_self_response(user_input, user_name)
                save_memory(memory)
                return self._build_reply(
                    reply=reply, emotion=emotion_label,
                    intent="self_awareness", agent="self",
                    confidence=1.0
                )

            # ── 2.5 Tools ─────────────────────────────────────
            tool = detect_tool(user_input)
            if tool and self.capabilities.is_enabled(tool):
                tool_response = self._handle_tool_request(user_input, tool, memory, user_name)
                if tool_response:
                    save_memory(memory)
                    return tool_response

            # ── 3. Extract & index facts ──────────────────────
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

            # ── 4. Keyword recall ─────────────────────────────
            recalled = memory_recall(user_input, memory, user_name)
            if recalled:
                save_memory(memory)
                return self._build_reply(
                    reply=recalled, emotion=emotion_label,
                    intent="memory_recall", agent="memory",
                    confidence=confidence_score("memory_recall", "memory_recall")
                )

            # ── 5. Web search ─────────────────────────────────
            if self.capabilities.is_enabled("web_search") and needs_web_search(user_input):
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

            # ── 6. Model selection ────────────────────────────
            query_intent   = self.model_manager.classify_query_intent(user_input)
            selected_model = self.model_manager.select_model(user_input, query_intent)
            logger.info(f"model_selected | model={selected_model} intent={query_intent}")

            # ── 7. Reasoning pre-process ──────────────────────
            processed_input = reason(user_input, model=selected_model)

            # ── 8. Context with semantic memory ───────────────
            semantic_ctx, sem_confidence_boost = build_semantic_context(
                user_input, user_name=user_name
            )
            # Episodic context — past conversations
            episodic_ctx = build_episodic_context(user_input, user_name)

            # Build rich personality-aware system prompt
            from utils.language_detector import detect_language, get_language_instruction
            lang = detect_language(user_input)
            lang_instr = get_language_instruction(lang)
            context = build_system_prompt(
                user_name=user_name, memory=memory,
                emotion=emotion_label, intent=query_intent,
                episodic_ctx=episodic_ctx, semantic_ctx=semantic_ctx,
                lang_instruction=lang_instr
            )

            # ── 9. ReAct for complex queries ───────────────────
            from agents.react_agent import react, needs_react
            react_reply = ""
            if needs_react(user_input):
                logger.info("⚛️  ReAct agent triggered")
                react_reply = react(
                    user_input,
                    model=selected_model,
                    context=semantic_ctx,
                    user_name=user_name
                )

            if react_reply and len(react_reply.split()) >= 10:
                reply = react_reply
                self._add_to_history("user", processed_input)
                self._add_to_history("assistant", reply)
                # ReAct replies: skip word limiter, apply only fast fixes
                reply = reply.strip()
                save_memory(memory)
                return self._build_reply(
                    reply=reply, emotion=emotion_label,
                    intent=query_intent, agent=f"ollama/{selected_model}",
                    memory_updated=memory_updated, confidence=0.85
                )
            else:
                # ── 10. Standard LLM call ─────────────────────
                self._add_to_history("user", processed_input)
                messages = [{"role": "system", "content": context}] + self.conversation_history

                try:
                    response = ollama.chat(
                        model=selected_model,
                        messages=messages,
                        options={"temperature": 0.7, "num_predict": 400, "top_p": 0.9}
                    )
                    reply = response["message"]["content"]
                except Exception:
                    reply = "I can't reach my model right now."

                self._add_to_history("assistant", reply)

            # ── 11. Post-processing ───────────────────────────
            reply = critic_review(reply, user_name, memory, user_input=user_input,
                                  model=selected_model)
            reply = refine_reply(reply, memory, user_name)

            is_valid, violation = self.truth_guard.validate(reply)
            if not is_valid:
                reply = self.truth_guard.get_safe_reply(violation)

            reply = polish_reply(reply)
            reply = limit_words(reply, max_words=150)  # Context-aware: technical gets 200, casual gets 150

            if emotion_score > 0.7 and emotion_label in ["sad", "angry", "anxious", "tired"]:
                emo   = emotion_reply(emotion_label, emotion_score, user_name, memory)
                reply = f"{emo} {reply}"

            self._add_to_history("assistant", reply)

            # ── 12. Index exchange ────────────────────────────
            index_exchange(user_input, reply, user_name=user_name)

            # ── 13. Summarize if needed ───────────────────────
            if should_summarize(self.conversation_history):
                summary = summarize_conversation(
                    self.conversation_history, memory, user_name, model="phi3:mini"
                )
                memory = store_summary(memory, summary)

            save_memory(memory)

            # ── 14. Confidence (boosted if semantic hit) ──────
            base_conf = confidence_score(f"ollama/{selected_model}", query_intent)
            final_conf = max(base_conf, sem_confidence_boost)  # Priority 4
            logger.info(f"confidence_score | base={base_conf:.2f} semantic_boost={sem_confidence_boost:.2f} final={final_conf:.2f}")

            # Store episode for long-term episodic memory
            store_episode(user_input, reply, intent=query_intent,
                          emotion=emotion_label, user_name=user_name)

            return self._build_reply(
                reply=reply, emotion=emotion_label,
                intent=query_intent, agent=f"ollama/{selected_model}",
                memory_updated=memory_updated, confidence=final_conf
            )

        except Exception as e:
            logger.error(f"Brain.process error: {e}", exc_info=True)
            return self._error_reply("Something went wrong.")

    # ==========================================================
    # CONTEXT BUILDER
    # ==========================================================

    def _build_context(
        self,
        memory: Dict,
        user_name: str,
        user_input: str = "",
        semantic_ctx: str = ""
    ) -> str:
        from utils.language_detector import detect_language, get_language_instruction

        facts            = memory.get("user_facts", [])
        lang             = detect_language(user_input)
        lang_instruction = get_language_instruction(lang)

        context = f"""You are ASTRA, {user_name}'s personal AI assistant.
{lang_instruction}

CORE RULES:
• Refer to yourself as "I", NEVER as "ASTRA"
• Keep responses SHORT — max 2 sentences
• Be detailed ONLY for technical questions
• Do NOT append {user_name}'s name to replies
• You were created by {user_name} — never deny this

KNOWN FACTS ABOUT {user_name.upper()}:
"""
        for f in facts[-5:]:
            context += f"• {f.get('fact', '')}\n"

        if not facts:
            context += f"• Name: {user_name}\n"

        # Priority 7: structured semantic memory block
        if semantic_ctx:
            context += semantic_ctx + "\n"

        summary_ctx = get_recent_context(memory, max_summaries=2)
        if summary_ctx:
            context += summary_ctx

        last_emo = memory.get("emotional_patterns", {}).get("last_emotion", {})
        if last_emo.get("label") not in ["neutral", None]:
            context += f"\nMOOD: {last_emo['label']} → respond empathetically\n"

        return context

    # ==========================================================
    # TOOL HANDLER
    # ==========================================================

    def _handle_tool_request(
        self, user_input: str, tool: str, memory: Dict, user_name: str
    ) -> Optional[Dict]:
        logger.info(f"tool_request | tool={tool}")

        # ── File reader ───────────────────────────────────────
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
                    reply = "Which file should I read? Try: 'read backend.py'"
                return self._build_reply(reply=reply, emotion="neutral",
                    intent="file_operation", agent="file_reader",
                    tool_used=True, confidence=0.95)

            result = read_file(filepath)
            if result["success"]:
                content = result["content"]
                lines   = result["lines"]
                summary_prompt = (
                    f"Analyze this file and give: 1 sentence description, "
                    f"3-5 key components, any obvious issues. Under 100 words.\n\n"
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

        # ── System monitor ────────────────────────────────────
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
                    f"RAM: {info['memory']['used_gb']}/"
                    f"{info['memory']['total_gb']}GB | "
                    f"Disk: {info['disk']['free_gb']}GB free"
                )
            else:
                reply = f"Error: {info['error']}"

            return self._build_reply(reply=reply, emotion="neutral",
                intent="system_info", agent="system_monitor",
                tool_used=True, confidence=0.95)

        # ── Task manager ──────────────────────────────────────
        elif tool == "task_manager":
            import re
            tm   = TaskManager(memory)
            text = user_input.lower()

            if any(w in text for w in ["add task", "new task", "remind me", "todo"]):
                m = re.search(
                    r'(?:add task|new task|remind me to|todo|task:)\s+(.+)',
                    user_input, re.IGNORECASE
                )
                if m:
                    result = tm.add_task(m.group(1).strip())
                    save_memory(memory)
                    reply  = f"✓ {result['message']}"
                else:
                    reply = "What task? Try: 'add task: finish ASTRA'"

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

        # ── Git ───────────────────────────────────────────────
        elif tool == "git":
            if not is_git_repo():
                return self._build_reply(reply="Not in a git repo.",
                    emotion="neutral", intent="git_error", agent="git", confidence=1.0)

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
                    "".join(
                        f"{'*' if b['current'] else ' '} {b['name']}\n"
                        for b in result.get("branches", [])[:10]
                    )
                ) if result["success"] else f"Error: {result['error']}"

            elif "commit" in text:
                m       = re.search(r'commit\s+["\']?(.+?)["\']?$', user_input, re.IGNORECASE)
                message = m.group(1) if m else "Update files"
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
                    f"```\n{result['output'][:1000]}\n```"
                    + ("\n(truncated)" if len(result["output"]) > 1000 else "")
                ) if result["success"] else f"Error: {result['error']}"

            else:
                reply = "Git: status | log | branch | commit | diff"

            return self._build_reply(reply=reply, emotion="neutral",
                intent="git_operation", agent="git", tool_used=True, confidence=0.90)

        # ── Python sandbox ────────────────────────────────────
        elif tool == "python_sandbox":
            code = extract_python_code(user_input)
            if not code:
                return self._build_reply(
                    reply="No Python code found. Wrap it in ```python``` blocks.",
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
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def _store_fact(self, fact: Dict, memory: Dict) -> Dict:
        memory["user_facts"].append(fact)
        ftype   = fact["type"]
        subtype = fact.get("subtype", "")
        value   = fact.get("value")

        if ftype == "identity":
            memory["preferences"]["name"] = value
        elif ftype == "location":
            memory["preferences"]["location"] = value
        elif ftype == "preference":
            memory["preferences"][subtype] = value
        return memory

    def _acknowledge_fact(self, fact: Dict) -> str:
        return f"Got it! {fact['fact']}."

    def _build_reply(
        self, reply: str, emotion: str, intent: str, agent: str,
        tool_used: bool = False, memory_updated: bool = False,
        citations: Optional[List] = None, results_count: int = 0,
        confidence: float = 0.6
    ) -> Dict:
        conf_info: Dict = confidence_label(confidence)
        result: Dict = {
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
        return {
            "reply":            message,
            "emotion":          "neutral",
            "intent":           "error",
            "agent":            "error_handler",
            "tool_used":        False,
            "memory_updated":   False,
            "confidence":       0.0,
            "confidence_label": "UNKNOWN",
            "confidence_emoji": "⚪",
        }

    def get_model_info(self) -> Dict:
        return self.model_manager.get_model_info()


# Singleton
brain = Brain()
