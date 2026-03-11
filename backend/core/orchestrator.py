from core.self_improve import SelfImprovementEngine
_self_improve = SelfImprovementEngine()

import logging
import time
import os
import requests
import ollama
from typing import Dict, List, Optional, Tuple

from utils.logger import agent_logger, chat_logger, system_logger, log_event
from utils.timeout import timeout

TASK_VIEW_TRIGGERS = [
    "pending task", "see tasks", "view tasks", "what are my tasks",
    "show tasks", "list tasks", "my tasks"
]

DEVICE_TRIGGERS = [
    "turn on", "turn off", "switch on", "switch off",
    "dim", "brighten", "set brightness", "set color",
    "lock", "unlock", "scan devices", "what devices",
    "show devices", "connect to", "camera feed", "thermostat",
    "fan", "ac", "air conditioner", "robot vacuum"
]

try:
    from core.self_improve import log_response as _log_self
except Exception:
    _log_self = lambda *a, **k: None

logger = logging.getLogger(__name__)

GPU_HOST   = os.getenv("REMOTE_GPU_HOST", "")
LOCAL_HOST = "http://localhost:11434"

MAX_AGENT_STEPS = 5


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
        pass  # TODO: handle
    return local, "phi3:mini", "CPU"


VISION_TRIGGERS = [
    "see", "look", "show", "camera", "finger", "hand", "hold",
    "what is this", "what's this", "what am i doing", "what do you see",
    "describe", "count", "how many", "can you see", "do you see",
    "my hand", "my face", "my room", "through camera", "this device",
    "this phone", "this object", "tell me what i", "my background"
]

CHAT_SHORTCUTS = {
    "greeting": {
        "triggers": ["hello", "hi", "hii", "hi astra", "hey astra", "hey",
                     "good morning", "good night", "namaste", "kaise ho", "how are you"],
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


# ── Multi-tool parallel detector ────────────────────────────────────────
def detect_multiple_tools(text: str) -> list:
    """Detect all tools needed for a query — enables parallel execution."""
    t       = text.lower()
    found   = []

    tool_keywords = {
        "web_search":     ["weather", "news", "search", "latest", "google", "look up"],
        "tasks":          ["tasks", "todo", "pending task", "my tasks", "task list"],
        "calendar":       ["calendar", "schedule", "meeting", "appointment", "today's events"],
        "system_monitor": ["cpu", "ram", "memory", "disk", "system stats"],
        "git":            ["git", "commits", "what changed", "git status"],
    }

    for tool, keywords in tool_keywords.items():
        if any(k in t for k in keywords):
            found.append(tool)

    return found


def run_parallel_tools(text: str, context: dict = {}) -> dict:
    """Run all detected tools in parallel. Returns {tool: result}."""
    tools = detect_multiple_tools(text)
    if not tools:
        return {}
    if len(tools) == 1:
        from tools import dispatch_tool
        return {tools[0]: dispatch_tool(tools[0], text, context)}

    from parallel_tools import execute_tools
    results = execute_tools(tools, text, context)
    return {r["tool"]: r["result"] for r in results if "result" in r}

TOOL_TRIGGERS = {
    "whatsapp":   ["whatsapp", "send message to", "send whatsapp"],
    "web_search": ["search for", "google", "look up", "latest news",
                   "current price", "weather in", "who won", "news about"],
    "calendar":   ["add to calendar", "schedule meeting", "remind me at"],
    "system":     ["volume up", "volume down", "open app", "close app",
                   "take screenshot", "lock screen"],
    "git":        ["git status", "git log", "git commit", "git diff"],
    "tasks":      ["add task", "my tasks", "show tasks", "complete task", "pending task", "see task", "list task", "view task", "my pending", "what are my tasks", "show me my tasks"],
    "files":      ["read file", "open file", "show file"],
    "python":     ["```python", "run python", "execute python", "run this code"],
}

# Queries that benefit from the full agent loop
LOOP_TRIGGERS = [
    "research and", "find and summarize", "compare and", "analyze",
    "step by step", "how do i build", "walk me through", "best way to",
    "should i", "pros and cons", "explain how", "difference between",
    "recommend", "what do you think about", "help me understand",
    "create a plan", "design a", "implement"
]

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
    t = text.lower().strip()
    for name, data in CHAT_SHORTCUTS.items():
        if any(tr in t for tr in data["triggers"]):
            return ("chat", name)
    if has_image and any(tr in t for tr in VISION_TRIGGERS):
        return ("vision", "camera")
    for tool, triggers in TOOL_TRIGGERS.items():
        if any(tr in t for tr in triggers):
            return ("tool", tool)
    if any(tr in t for tr in LOOP_TRIGGERS):
        return ("loop", "complex")
    if any(tr in t for tr in PLAN_TRIGGERS):
        return ("plan", "multi_step")
    if any(tr in t for tr in REACT_TRIGGERS):
        return ("react", "reasoning")
    return ("llm", "general")


def _build_context(user_input: str) -> Dict:
    ctx = {"facts": "", "episodes": "", "user_name": "Arnav"}
    try:
        from memory.memory_engine import load_memory
        mem = load_memory()
        ctx["user_name"] = mem.get("preferences", {}).get("name", "Arnav")
        facts = mem.get("user_facts", [])
        if facts:
            ctx["facts"] = " | ".join(f["fact"] for f in facts[-5:])
        from memory.episodic import build_episodic_context
        ctx["episodes"] = build_episodic_context(user_input, ctx["user_name"])

        # Knowledge graph context
        from knowledge.graph import build_graph_context
        graph_ctx = build_graph_context(user_input, ctx["user_name"])
        if graph_ctx:
            ctx["graph"] = graph_ctx
    except Exception as e:
        log_event(system_logger, "context_build_failed", error=str(e))
    return ctx


def _run_tool(tool: str, text: str) -> Optional[Dict]:
    log_event(agent_logger, "tool_start", tool=tool, input=text[:80])
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
            from memory.memory_engine import load_memory
            result = str(TaskManager(load_memory()).list_tasks())
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
            log_event(agent_logger, "tool_success", tool=tool, result_len=len(str(result)))
            return {"result": result, "confidence": 0.95, "tool": tool}
        else:
            log_event(agent_logger, "tool_no_result", tool=tool)

    except Exception as e:
        log_event(agent_logger, "tool_error", tool=tool, error=str(e))

    return None


def _react_loop(user_input: str, context: Dict) -> Optional[str]:
    client, model, hw = _client_and_model()
    log_event(agent_logger, "react_start", model=model, hw=hw, input=user_input[:80])

    system = f"""You are ASTRA, a smart AI assistant.
Solve the user's question using this format EXACTLY:

Thought: what you are thinking
Action: [tool_name or "answer"] — pick one of: web_search, recall_memory, calculate, answer
Observation: result of the action

Repeat up to {MAX_AGENT_STEPS} times. When ready write:
Final Answer: your answer

User context: {context.get('facts', '')}
{context.get('episodes', '')}"""

    messages    = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_input}
    ]
    steps       = 0
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

            import re
            thought_m = re.search(r'Thought:(.*?)(?:Action:|$)', output, re.DOTALL)
            action_m  = re.search(r'Action:\s*\[?(\w+)\]?', output)
            thought   = thought_m.group(1).strip()[:120] if thought_m else ""
            action    = action_m.group(1) if action_m else "none"

            log_event(agent_logger, "react_step",
                      step=steps, action=action, thought=thought,
                      has_final="Final Answer:" in output)

            if "Final Answer:" in output:
                final = output.split("Final Answer:")[-1].strip()
                answer = final.split("\n\n")[0].strip()
                log_event(agent_logger, "react_done", steps=steps, answer=answer[:120])
                return answer

            if action_m:
                action_name = action_m.group(1).lower()
                observation = ""
                if action_name == "web_search":
                    query       = thought_m.group(1).strip() if thought_m else user_input
                    tool_result = _run_tool("web_search", query)
                    observation = tool_result["result"][:300] if tool_result else "No results found"
                elif action_name == "recall_memory":
                    from memory.memory_recall import memory_recall
                    from memory.memory_engine import load_memory
                    observation = memory_recall(user_input, load_memory(), "Arnav") or "Nothing found"
                elif action_name == "calculate":
                    observation = "Use math to compute the answer"
                else:
                    break

                log_event(agent_logger, "react_observation",
                          step=steps, action=action_name,
                          observation=observation[:120])
                messages.append({"role": "assistant", "content": output})
                messages.append({"role": "user", "content": f"Observation: {observation}\n\nContinue."})
            else:
                break

        except Exception as e:
            log_event(agent_logger, "react_error", step=steps, error=str(e))
            break

    if "Final Answer:" in full_output:
        return full_output.split("Final Answer:")[-1].strip().split("\n\n")[0]
    lines = [l.strip() for l in full_output.split("\n")
             if l.strip() and not l.startswith(("Thought:", "Action:", "Observation:"))]
    return lines[-1] if lines else None


def _plan_and_execute(user_input: str, context: Dict) -> Optional[str]:
    from agents.planner import decompose, execute_plan
    log_event(agent_logger, "plan_start", input=user_input[:80])
    steps  = decompose(user_input)
    log_event(agent_logger, "plan_steps",
              count=len(steps), steps=[s.get("action") for s in steps])
    result = execute_plan(steps, user_input)
    log_event(agent_logger, "plan_done", result_len=len(result) if result else 0)
    return result if result else None


def _llm_reply(text: str, context: Dict) -> str:
    client, model, hw = _client_and_model()
    log_event(system_logger, "llm_call", model=model, hw=hw, input=text[:80])

    system   = (
        "You are Astra, a smart personal AI assistant. "
        "Answer in 1-2 sentences max. Be accurate and direct. "
        "Never make up facts. If unsure say so briefly."
    )
    messages = [{"role": "system", "content": system}]

    memory_ctx = ""
    if context.get("facts"):
        memory_ctx += f"Facts about user: {context['facts']}\n"
    if context.get("episodes"):
        memory_ctx += context["episodes"]
    if context.get("graph"):
        memory_ctx += "\n" + context["graph"]
    if memory_ctx:
        messages.append({"role": "system",
                          "content": f"Memory context:\n{memory_ctx}"})

    messages.append({"role": "user", "content": text})

    response = client.chat(
        model=model,
        messages=messages,
        options={"temperature": 0.5, "num_predict": 120}
    )
    reply = response["message"]["content"].strip()
    log_event(system_logger, "llm_reply", model=model, reply_len=len(reply))
    return reply


def _vision_reply(text: str, image_b64: str) -> str:
    gpu_up = _gpu_alive()
    client = ollama.Client(host=GPU_HOST if gpu_up else LOCAL_HOST)
    hw     = "GPU" if gpu_up else "CPU"
    log_event(agent_logger, "vision_start", hw=hw, question=text[:80])

    response = client.chat(
        model="llava:7b",
        messages=[{
            "role":    "user",
            "content": (
                "You are Astra, a personal AI with a live camera. "
                "Answer ONLY what is asked. Do not describe the full scene. "
                "If asked about fingers — count carefully. "
                "Keep answer to 1 sentence. "
                f"Question: {text}"
            ),
            "images": [image_b64]
        }],
        options={"temperature": 0.1, "num_predict": 60}
    )
    reply = response["message"]["content"].strip()
    log_event(agent_logger, "vision_done", reply=reply[:80])
    return reply


def _truth_guard(reply: str) -> str:
    try:
        from core.truth_guard import TruthGuard
        tg = TruthGuard()
        valid, violation = tg.validate(reply)
        if not valid:
            log_event(system_logger, "truth_guard_block", violation=violation)
            return tg.get_safe_reply(violation)
    except Exception as e:
        log_event(system_logger, "truth_guard_error", error=str(e))
    return reply


def _critic(reply: str, user_input: str) -> str:
    try:
        from agents.critic import critic_review
        return critic_review(reply, "Arnav", {}, user_input=user_input)
    except Exception as e:
        log_event(system_logger, "critic_error", error=str(e))
    return reply


def _store(user_input: str, reply: str, intent: str):
    try:
        from memory.episodic import store_episode
        store_episode(user_input, reply, intent=intent, user_name="Arnav")
    except Exception as e:
        log_event(system_logger, "memory_store_error", error=str(e))


class Orchestrator:

    @timeout(30)
    def run(self, user_input: str, image_b64: Optional[str] = None) -> Dict:
        start  = time.time()
        intent = "general"
        agent  = "astra"

        log_event(chat_logger, "request", input=user_input[:120])

        try:
            has_image               = bool(image_b64)
            input_type, subcategory = _detect_input_type(user_input, has_image)
            intent = subcategory
            log_event(chat_logger, "intent_detected",
                      input_type=input_type, subcategory=subcategory)

            # ── Instant shortcuts ─────────────────────────────
            if input_type == "chat":
                reply = CHAT_SHORTCUTS[subcategory]["reply"]
                agent = "shortcut"
                return self._out(reply, intent, agent, 1.0, start)

            # ── Vision ────────────────────────────────────────
            if input_type == "vision" and image_b64:
                reply = _vision_reply(user_input, image_b64)
                agent = "llava:7b"
                _store(user_input, reply, intent)
                return self._out(reply, intent, agent, 0.85, start)

            context = _build_context(user_input)

            # ── Tool direct ───────────────────────────────────
            if input_type == "tool":
                tool_out = _run_tool(subcategory, user_input)
                if tool_out:
                    reply = tool_out["result"]
                    agent = subcategory
                    _store(user_input, reply, intent)
                    return self._out(reply, intent, agent,
                                     tool_out["confidence"], start)

            # ── Autonomous Agent Loop (complex queries) ───────
            if input_type == "loop":
                from core.agent_loop import agent_loop
                log_event(chat_logger, "loop_triggered", input=user_input[:80])
                loop_result = agent_loop.run(user_input, context)
                reply = loop_result.final_reply
                reply = _truth_guard(reply)
                agent = f"agent_loop/{loop_result.iterations}steps"
                _store(user_input, reply, intent)
                return self._out(reply, intent, agent,
                                 loop_result.confidence, start,
                                 loop_steps=loop_result.iterations)

            # ── Planner ───────────────────────────────────────
            if input_type == "plan":
                result = _plan_and_execute(user_input, context)
                if result:
                    agent = "planner"
                    _store(user_input, result, intent)
                    return self._out(result, intent, agent, 0.85, start)

            # ── ReAct ─────────────────────────────────────────
            if input_type == "react":
                result = _react_loop(user_input, context)
                if result:
                    agent  = "react+mistral"
                    result = _truth_guard(result)
                    result = _critic(result, user_input)
                    _store(user_input, result, intent)
                    return self._out(result, intent, agent, 0.85, start)

            # ── Direct LLM ────────────────────────────────────
            raw   = _llm_reply(user_input, context)
            agent = "mistral"
            raw   = _truth_guard(raw)
            raw   = _critic(raw, user_input)
            _store(user_input, raw, intent)
            return self._out(raw, intent, agent, 0.80, start)

        except Exception as e:
            log_event(chat_logger, "request_error", error=str(e))
            return self._out(f"Error: {e}", "error", "error", 0.0, start)

    def _out(self, reply: str, intent: str, agent: str,
             confidence: float, start: float, **extra) -> Dict:
        elapsed = round(time.time() - start, 2)
        log_event(chat_logger, "response",
                  agent=agent, intent=intent,
                  confidence=confidence, elapsed=elapsed,
                  reply=reply[:120])
        out = {
            "reply":            reply or "Say that again?",
            "intent":           intent,
            "agent":            agent,
            "confidence":       confidence,
            "confidence_label": "HIGH"   if confidence >= 0.85 else
                                "MEDIUM" if confidence >= 0.6  else "LOW",
            "confidence_emoji": "��" if confidence >= 0.85 else
                                "🟡" if confidence >= 0.6  else "🔴",
            "emotion":          "neutral",
            "tool_used":        False,
            "memory_updated":   False,
            "elapsed":          elapsed,
        }
        out.update(extra)
        return out


orchestrator = Orchestrator()