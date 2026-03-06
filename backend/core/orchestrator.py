# ==========================================
# core/orchestrator.py — v3.0
# Correct pipeline:
# Input → Intent+Type → Memory → Planner
# → ReAct(Thought/Action/Observe loop)
# → Tool → LLM → TruthGuard → Critic
# → Memory Store → Reply
# ==========================================

import logging
import time
import os
import requests
import ollama
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

GPU_HOST   = "http://100.113.54.3:11434"
LOCAL_HOST = "http://localhost:11434"

MAX_AGENT_STEPS = 5   # rate limiter — no infinite loops


# ══════════════════════════════════════════
# HARDWARE
# ══════════════════════════════════════════

def _gpu_alive() -> bool:
    try:
        return requests.get(GPU_HOST, timeout=1).status_code == 200
    except Exception:
        return False

def _client_and_model() -> Tuple:
    if _gpu_alive():
        return ollama.Client(host=GPU_HOST), "mistral:latest", "GPU"
    local = ollama.Client(host=LOCAL_HOST)
    try:
        names = [m.get("model", m.get("name","")) for m in local.list().get("models",[])]
        for m in ["llama3.2:3b", "mistral:latest", "phi3:mini"]:
            if any(m in n for n in names):
                return local, m, "CPU"
    except Exception:
        pass
    return local, "phi3:mini", "CPU"


# ══════════════════════════════════════════
# INTENT + INPUT TYPE DETECTION
# ══════════════════════════════════════════

VISION_TRIGGERS = [
    "see", "look", "show", "camera", "finger", "hand", "hold",
    "what is this", "what's this", "what am i doing", "what do you see",
    "describe", "count", "how many", "can you see", "do you see",
    "my hand", "my face", "my room", "through camera", "this device",
    "this phone", "this object", "tell me what i", "my background"
]

CHAT_SHORTCUTS = {
    "greeting": {
        "triggers": ["hello", "hi astra", "hey astra", "good morning",
                     "good night", "namaste", "kaise ho", "how are you"],
        "reply":    "Hey! What's up?"
    },
    "identity": {
        "triggers": ["your name", "who are you", "what are you",
                     "tum kaun", "aap kaun"],
        "reply":    "I'm ASTRA, your personal AI assistant built by Arnav."
    },
    "creator": {
        "triggers": ["who made you", "who built you", "kisne banaya"],
        "reply":    "Arnav built me. Pretty cool right?"
    },
    "farewell": {
        "triggers": ["bye", "goodbye", "see you later", "cya"],
        "reply":    "Bye! See you soon."
    },
    "capable": {
        "triggers": ["what can you do", "your features", "your abilities"],
        "reply":    "I can chat, answer questions, see through camera, search the web, manage tasks, run code, and remember things."
    },
}

TOOL_TRIGGERS = {
    "whatsapp":   ["whatsapp", "send message to", "send whatsapp"],
    "web_search": ["search for", "google", "look up", "latest news",
                   "current price", "weather in", "who won", "news about"],
    "calendar":   ["add to calendar", "schedule meeting", "remind me at"],
    "system":     ["volume up", "volume down", "open app", "close app",
                   "take screenshot", "lock screen"],
    "git":        ["git status", "git log", "git commit", "git diff"],
    "tasks":      ["add task", "my tasks", "show tasks", "complete task"],
    "files":      ["read file", "open file", "show file"],
    "python":     ["```python", "run python", "execute python", "run this code"],
}

PLAN_TRIGGERS = [
    "research and", "find and summarize", "search and summarize",
    "compare and", "analyze and write", "step by step plan",
    "how do i build", "walk me through building"
]

REACT_TRIGGERS = [
    "why", "how does", "explain how", "what causes",
    "difference between", "compare", "pros and cons",
    "should i", "which is better", "analyze", "step by step"
]


def _detect_input_type(text: str, has_image: bool) -> Tuple[str, str]:
    """
    Returns (input_type, subcategory).
    Types: chat | vision | tool | plan | react | llm
    """
    t = text.lower().strip()

    # 1. Chat shortcuts — instant
    for name, data in CHAT_SHORTCUTS.items():
        if any(tr in t for tr in data["triggers"]):
            return ("chat", name)

    # 2. Vision — image present AND vision words used
    if has_image and any(tr in t for tr in VISION_TRIGGERS):
        return ("vision", "camera")

    # 3. Tool — explicit tool trigger
    for tool, triggers in TOOL_TRIGGERS.items():
        if any(tr in t for tr in triggers):
            return ("tool", tool)

    # 4. Multi-step plan
    if any(tr in t for tr in PLAN_TRIGGERS):
        return ("plan", "multi_step")

    # 5. ReAct reasoning
    if any(tr in t for tr in REACT_TRIGGERS):
        return ("react", "reasoning")

    # 6. Default — LLM
    return ("llm", "general")


# ══════════════════════════════════════════
# CONTEXT BUILDER
# ══════════════════════════════════════════

def _build_context(user_input: str) -> Dict:
    """
    Gather: memory facts + episodic history + user prefs.
    Returns context dict used by LLM call.
    """
    ctx = {"facts": "", "episodes": "", "user_name": "Arnav"}

    try:
        from memory.memory_engine import load_memory
        mem = load_memory()
        ctx["user_name"] = mem.get("preferences", {}).get("name", "Arnav")

        # User facts
        facts = mem.get("user_facts", [])
        if facts:
            ctx["facts"] = " | ".join(f["fact"] for f in facts[-5:])

        # Episodic context
        from memory.episodic import build_episodic_context
        ctx["episodes"] = build_episodic_context(user_input, ctx["user_name"])
    except Exception as e:
        logger.warning(f"Context build failed: {e}")

    return ctx


# ══════════════════════════════════════════
# TOOL EXECUTOR
# ══════════════════════════════════════════

def _run_tool(tool: str, text: str) -> Optional[Dict]:
    """
    Execute tool. Returns {result, confidence} or None.
    """
    try:
        result = None

        if tool == "whatsapp":
            from tools.whatsapp_tool import handle_whatsapp_command
            result = handle_whatsapp_command(text)

        elif tool == "web_search":
            from tools.web_search import handle_search_command
            result = handle_search_command(text)

        elif tool == "calendar":
            from tools.calendar_tool import handle_calendar_command
            result = handle_calendar_command(text)

        elif tool == "system":
            from tools.system_controller import handle_system_command
            result = handle_system_command(text)

        elif tool == "git":
            from tools.git_tool import git_status
            result = git_status().get("output", "No git info")

        elif tool == "tasks":
            from tools.task_manager import TaskManager
            result = str(TaskManager().list_tasks())

        elif tool == "files":
            from tools.file_reader import extract_filepath, read_file
            path = extract_filepath(text)
            result = read_file(path) if path else None

        elif tool == "python":
            from tools.python_sandbox import propose_python_execution, extract_python_code
            code = extract_python_code(text)
            if code:
                result = str(propose_python_execution(code))

        if result:
            return {"result": result, "confidence": 0.95, "tool": tool}

    except Exception as e:
        logger.error(f"Tool {tool} error: {e}")

    return None


# ══════════════════════════════════════════
# REACT AGENT — Thought/Action/Observe loop
# ══════════════════════════════════════════

def _react_loop(user_input: str, context: Dict) -> Optional[str]:
    """
    ReAct loop with proper Thought→Action→Observation→Thought cycle.
    Max MAX_AGENT_STEPS iterations.
    """
    client, model, hw = _client_and_model()
    logger.info(f"⚛️ ReAct on {hw} | model={model}")

    system = f"""You are ASTRA, a smart AI assistant.
Solve the user's question using this format EXACTLY:

Thought: what you are thinking
Action: [tool_name or "answer"] — pick one of: web_search, recall_memory, calculate, answer
Observation: result of the action

Repeat Thought/Action/Observation up to {MAX_AGENT_STEPS} times.
When ready, write:
Final Answer: your answer

User context: {context.get('facts', '')}
{context.get('episodes', '')}"""

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_input}
    ]

    steps = 0
    full_output = ""

    while steps < MAX_AGENT_STEPS:
        try:
            response = client.chat(
                model=model,
                messages=messages,
                options={"temperature": 0.3, "num_predict": 300}
            )
            output = response["message"]["content"].strip()
            full_output += output + "\n"
            steps += 1

            logger.info(f"⚛️ Step {steps}: {output[:80]}")

            # Check for Final Answer
            if "Final Answer:" in output:
                final = output.split("Final Answer:")[-1].strip()
                return final.split("\n\n")[0].strip()

            # Check for tool action
            import re
            action_match = re.search(r'Action:\s*\[?(\w+)\]?', output)
            if action_match:
                action = action_match.group(1).lower()
                observation = ""

                if action == "web_search":
                    # Extract search query from Thought
                    thought = re.search(r'Thought:(.*?)(?:Action:|$)', output, re.DOTALL)
                    query = thought.group(1).strip() if thought else user_input
                    tool_result = _run_tool("web_search", query)
                    observation = tool_result["result"][:300] if tool_result else "No results found"

                elif action == "recall_memory":
                    from memory.memory_recall import memory_recall
                    from memory.memory_engine import load_memory
                    observation = memory_recall(user_input, load_memory(), "Arnav") or "Nothing found in memory"

                elif action == "calculate":
                    observation = "Use math to compute the answer"

                else:
                    # answer — break and let LLM reply
                    break

                # Feed observation back
                messages.append({"role": "assistant", "content": output})
                messages.append({"role": "user",      "content": f"Observation: {observation}\n\nContinue."})

            else:
                # No action found — take the last meaningful line as answer
                break

        except Exception as e:
            logger.error(f"ReAct step {steps} error: {e}")
            break

    # Extract best answer from full output
    if "Final Answer:" in full_output:
        return full_output.split("Final Answer:")[-1].strip().split("\n\n")[0]

    # Last non-empty line as fallback
    lines = [l.strip() for l in full_output.split("\n")
             if l.strip() and not l.startswith(("Thought:", "Action:", "Observation:"))]
    return lines[-1] if lines else None


# ══════════════════════════════════════════
# PLANNER — multi-step decomposition
# ══════════════════════════════════════════

def _plan_and_execute(user_input: str, context: Dict) -> Optional[str]:
    """Decompose complex task and execute each step."""
    from agents.planner import decompose, execute_plan
    steps  = decompose(user_input)
    result = execute_plan(steps, user_input)
    return result if result else None


# ══════════════════════════════════════════
# LLM — direct answer with full context
# ══════════════════════════════════════════

def _llm_reply(text: str, context: Dict) -> str:
    client, model, hw = _client_and_model()
    logger.info(f"💬 LLM: {model} on {hw}")

    system = (
        "You are Astra, a smart personal AI assistant. "
        "Answer in 1-2 sentences max. Be accurate and direct. "
        "Never make up facts. If unsure say so briefly."
    )

    messages = [{"role": "system", "content": system}]

    # Inject memory context
    memory_ctx = ""
    if context.get("facts"):
        memory_ctx += f"Facts about user: {context['facts']}\n"
    if context.get("episodes"):
        memory_ctx += context["episodes"]
    if memory_ctx:
        messages.append({"role": "system", "content": f"Memory context:\n{memory_ctx}"})

    messages.append({"role": "user", "content": text})

    response = client.chat(
        model=model,
        messages=messages,
        options={"temperature": 0.5, "num_predict": 120}
    )
    return response["message"]["content"].strip()


# ══════════════════════════════════════════
# VISION
# ══════════════════════════════════════════

def _vision_reply(text: str, image_b64: str) -> str:
    gpu_up = _gpu_alive()
    client = ollama.Client(host=GPU_HOST if gpu_up else LOCAL_HOST)
    hw     = "GPU" if gpu_up else "CPU"
    logger.info(f"👁️ llava:7b on {hw}")

    response = client.chat(
        model="llava:7b",
        messages=[{
            "role":    "user",
            "content": (
                "You are Astra, a personal AI with a live camera. "
                "Answer ONLY what is asked. Do not describe the full scene. "
                "If asked about fingers — count carefully and say the number. "
                "Keep answer to 1 sentence. "
                f"Question: {text}"
            ),
            "images": [image_b64]
        }],
        options={"temperature": 0.1, "num_predict": 60}
    )
    return response["message"]["content"].strip()


# ══════════════════════════════════════════
# TRUTH GUARD + CRITIC
# ══════════════════════════════════════════

def _truth_guard(reply: str) -> str:
    try:
        from core.truth_guard import TruthGuard
        tg = TruthGuard()
        valid, violation = tg.validate(reply)
        if not valid:
            logger.warning(f"⚠️ TruthGuard: {violation}")
            return tg.get_safe_reply(violation)
    except Exception as e:
        logger.warning(f"TruthGuard failed: {e}")
    return reply


def _critic(reply: str, user_input: str) -> str:
    try:
        from agents.critic import critic_review
        return critic_review(reply, "Arnav", {}, user_input=user_input)
    except Exception as e:
        logger.warning(f"Critic failed: {e}")
    return reply


# ══════════════════════════════════════════
# MEMORY STORAGE
# ══════════════════════════════════════════

def _store(user_input: str, reply: str, intent: str):
    try:
        from memory.episodic import store_episode
        store_episode(user_input, reply, intent=intent, user_name="Arnav")
    except Exception as e:
        logger.warning(f"Memory store failed: {e}")


# ══════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════

class Orchestrator:

    def run(self, user_input: str, image_b64: Optional[str] = None) -> Dict:
        start  = time.time()
        intent = "general"
        agent  = "astra"

        try:
            # ── 1. Detect input type ──────────────────────────
            has_image = bool(image_b64)
            input_type, subcategory = _detect_input_type(user_input, has_image)
            intent = subcategory
            logger.info(f"🎯 {input_type}/{subcategory}")

            # ── 2. Chat shortcut — instant reply ──────────────
            if input_type == "chat":
                reply = CHAT_SHORTCUTS[subcategory]["reply"]
                agent = "shortcut"
                return self._out(reply, intent, agent, 1.0, start)

            # ── 3. Vision — llava sees image ──────────────────
            if input_type == "vision" and image_b64:
                reply = _vision_reply(user_input, image_b64)
                agent = "llava:7b"
                _store(user_input, reply, intent)
                return self._out(reply, intent, agent, 0.85, start)

            # ── 4. Memory recall ──────────────────────────────
            context = _build_context(user_input)

            # ── 5. Tool execution ─────────────────────────────
            if input_type == "tool":
                tool_out = _run_tool(subcategory, user_input)
                if tool_out:
                    reply = tool_out["result"]
                    agent = subcategory
                    _store(user_input, reply, intent)
                    return self._out(reply, intent, agent,
                                     tool_out["confidence"], start)

            # ── 6. Planner — multi-step tasks ─────────────────
            if input_type == "plan":
                result = _plan_and_execute(user_input, context)
                if result:
                    agent = "planner"
                    _store(user_input, result, intent)
                    return self._out(result, intent, agent, 0.85, start)

            # ── 7. ReAct — reasoning with tool loop ───────────
            if input_type == "react":
                result = _react_loop(user_input, context)
                if result:
                    agent  = "react+mistral"
                    # TruthGuard → Critic
                    result = _truth_guard(result)
                    result = _critic(result, user_input)
                    _store(user_input, result, intent)
                    return self._out(result, intent, agent, 0.85, start)

            # ── 8. LLM — direct answer ────────────────────────
            raw   = _llm_reply(user_input, context)
            agent = "mistral"

            # ── 9. TruthGuard first ───────────────────────────
            raw = _truth_guard(raw)

            # ── 10. Critic second ─────────────────────────────
            raw = _critic(raw, user_input)

            # ── 11. Store memory ──────────────────────────────
            _store(user_input, raw, intent)

            return self._out(raw, intent, agent, 0.80, start)

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return self._out(f"Error: {e}", "error", "error", 0.0, start)

    def _out(self, reply: str, intent: str, agent: str,
             confidence: float, start: float) -> Dict:
        elapsed = round(time.time() - start, 2)
        logger.info(f"✅ {elapsed}s | {agent} | {intent}")
        return {
            "reply":      reply or "Say that again?",
            "intent":     intent,
            "agent":      agent,
            "confidence": confidence,
            "emotion":    "neutral",
            "elapsed":    elapsed,
        }


orchestrator = Orchestrator()
