import asyncio
from core.llm_engine import LLMEngine as _LLMEngine
_llm = _LLMEngine()
import os
# ==========================================
# core/agent_loop.py — Autonomous Agent Loop
# Flow: Observe → Plan → Act → Reflect → Repeat
# Self-correcting with max_iterations cap
# ==========================================

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from utils.logger import agent_logger, log_event

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5
CONFIDENCE_THRESHOLD = 0.75


class LoopStatus(Enum):
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    TIMEOUT   = "timeout"


@dataclass
class AgentStep:
    iteration:   int
    thought:     str
    action:      str
    action_input: str
    observation: str
    confidence:  float
    elapsed:     float


@dataclass
class LoopResult:
    final_reply:  str
    steps:        List[AgentStep] = field(default_factory=list)
    status:       LoopStatus      = LoopStatus.DONE
    total_elapsed: float          = 0.0
    iterations:   int             = 0
    confidence:   float           = 0.0


# ══════════════════════════════════════════
# OBSERVE — understand what is being asked
# ══════════════════════════════════════════

def _observe(user_input: str, context: Dict) -> Dict:
    """
    Analyse the request and extract:
    - task type
    - complexity score
    - requires_tools flag
    - requires_reflection flag
    """
    t = user_input.lower()

    complexity = 1
    if len(user_input.split()) > 20:
        complexity += 1
    if any(w in t for w in ["and then", "after that", "first", "then", "finally"]):
        complexity += 1
    if any(w in t for w in ["compare", "analyze", "research", "build", "create", "implement"]):
        complexity += 1

    requires_tools = any(w in t for w in [
        "search", "file", "git", "run", "execute", "calendar",
        "task", "system", "code", "python", "weather", "news"
    ])

    requires_reflection = complexity >= 3 or any(w in t for w in [
        "best way", "should i", "what do you think", "advice",
        "recommend", "pros and cons", "compare"
    ])

    observation = {
        "input":               user_input,
        "complexity":          complexity,
        "requires_tools":      requires_tools,
        "requires_reflection": requires_reflection,
        "context":             context,
    }

    log_event(agent_logger, "observe",
              complexity=complexity,
              requires_tools=requires_tools,
              requires_reflection=requires_reflection)

    return observation


# ══════════════════════════════════════════
# PLAN — decompose into steps
# ══════════════════════════════════════════

def _plan(observation: Dict) -> List[Dict]:
    """
    Given observation, produce ordered execution plan.
    Returns list of {step, action, description} dicts.
    """
    user_input = observation["input"]
    complexity = observation["complexity"]

    # Tool queries — always check tools first before simple fallback
    if observation["requires_tools"] and not observation["requires_reflection"]:
        return [
            {"step": 1, "action": "tool_execute",  "description": user_input},
            {"step": 2, "action": "llm_reply",     "description": "summarise tool result"},
        ]

    # Simple queries — single step
    if complexity <= 1:
        return [{"step": 1, "action": "llm_reply", "description": user_input}]

    # Complex queries — full pipeline
    plan = [
        {"step": 1, "action": "memory_recall",  "description": f"recall context for: {user_input}"},
        {"step": 2, "action": "tool_execute",   "description": user_input},
        {"step": 3, "action": "llm_reply",      "description": user_input},
        {"step": 4, "action": "reflect",        "description": "check if answer is complete and correct"},
    ]

    log_event(agent_logger, "plan_created",
              steps=[p["action"] for p in plan],
              complexity=complexity)
    return plan


# ══════════════════════════════════════════
# ACT — execute one plan step
# ══════════════════════════════════════════

async def _act(step: Dict, user_input: str, context: Dict,
         previous_results: List[str]) -> Tuple[str, float]:
    """
    Execute a single plan step.
    Returns (result_text, confidence).
    """
    action = step["action"]
    log_event(agent_logger, "act_start", action=action, step=step["step"])

    try:
        if action == "memory_recall":
            return _act_memory(user_input, context)

        elif action == "tool_execute":
            return _act_tool(user_input, context)

        elif action == "llm_reply":
            prior = "\n".join(previous_results[-2:]) if previous_results else ""
            return _act_llm(user_input, context, prior)

        elif action == "reflect":
            if not previous_results:
                return "", 0.5
            return _act_reflect(user_input, previous_results[-1], context)

        else:
            return "", 0.0

    except Exception as e:
        log_event(agent_logger, "act_error", action=action, error=str(e))
        return "", 0.0


async def _act_memory(user_input: str, context: Dict) -> Tuple[str, float]:
    try:
        from memory.memory_recall import memory_recall
        from memory.memory_engine import load_memory
        from memory.semantic_recall import build_semantic_context

        mem    = load_memory()
        result = memory_recall(user_input, mem, context.get("user_name", "User"))
        sem, boost = build_semantic_context(user_input,
                                            user_name=context.get("user_name", "User"))
        combined = ""
        if result:
            combined += result
        if sem:
            combined += "\n" + sem
        return combined, boost if combined else 0.0
    except Exception as e:
        logger.warning(f"Memory recall failed: {e}")
        return "", 0.0


async def _act_tool(user_input: str, context: Dict) -> Tuple[str, float]:
    try:
        from tools.tool_router import detect_tool
        from core.orchestrator import _run_tool

        tool = detect_tool(user_input)
        if not tool:
            return "", 0.0

        result = _run_tool(tool, user_input)
        if result:
            return result["result"], result["confidence"]
        return "", 0.0
    except Exception as e:
        logger.warning(f"Tool execution failed: {e}")
        return "", 0.0


async def _act_llm(user_input: str, context: Dict, prior_results: str = "") -> Tuple[str, float]:
    try:
        import ollama
        import requests

        GPU_HOST   = os.getenv("REMOTE_GPU_HOST", "")

        try:
            alive = requests.get(GPU_HOST, timeout=1).status_code == 200
        except Exception:
            alive = False

        # routed through LLMEngine — no direct ollama coupling
        model  = _llm.select_model("reasoning") if alive else _llm.select_model("fast")

        system = (
            "You are ASTRA, a smart personal AI assistant. "
            "Be accurate, concise, direct. Max 3 sentences unless technical. "
            "Never hallucinate. If unsure, say so."
        )
        messages = [{"role": "system", "content": system}]

        if context.get("facts"):
            messages.append({"role": "system",
                              "content": f"User facts: {context['facts']}"})

        if prior_results:
            messages.append({"role": "system",
                              "content": f"Previous findings:\n{prior_results}"})

        messages.append({"role": "user", "content": user_input})

        try:
            import ollama
            resp = ollama.Client().chat(model=model, messages=messages,
                                        options={"num_predict": 300, "temperature": 0.65})
            return resp["message"]["content"].strip(), 0.75
        except Exception as e:
            return f"LLM error: {e}", 0.0

    except Exception as e:
        logger.error(f"LLM act failed: {e}")
        return "", 0.0


async def _act_reflect(user_input: str, draft_reply: str,
                 context: Dict) -> Tuple[str, float]:
    """
    Critic pass — check if the draft reply actually answers the question.
    Returns (improved_reply, confidence).
    """
    try:
        import ollama
        import requests

        GPU_HOST   = os.getenv("REMOTE_GPU_HOST", "")

        try:
            alive = requests.get(GPU_HOST, timeout=1).status_code == 200
        except Exception:
            alive = False

        # routed through LLMEngine — no direct ollama coupling
        model  = _llm.select_model("reasoning") if alive else _llm.select_model("fast")

        prompt = f"""You are reviewing an AI assistant's response.

Question: {user_input}
Draft response: {draft_reply}

Check:
1. Does it fully answer the question? (yes/no)
2. Are there any factual errors? (yes/no)
3. Is it too long or too short? (too_long/too_short/ok)

If all good → reply with just the word: APPROVED
If needs fixing → reply with the improved version only, no preamble.

Output:"""

        try:
            import ollama
            result = ollama.Client().chat(model=model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 200, "temperature": 0.1}
            )["message"]["content"].strip()
        except Exception as e:
            logger.error("reflect LLM call failed: %s", e)
            return draft_reply, 0.70
            log_event(agent_logger, "reflect_approved")
            return draft_reply, 0.95
        else:
            log_event(agent_logger, "reflect_improved",
                      original_len=len(draft_reply), new_len=len(result))
            return result, 0.90

    except Exception as e:
        logger.warning(f"Reflect failed: {e}")
        return draft_reply, 0.75


# ══════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════

class AgentLoop:
    """
    Autonomous agent loop.
    Observe → Plan → Act → Reflect → Repeat until done or max_iterations.
    """

    def __init__(self, max_iterations: int = MAX_ITERATIONS):
        self.max_iterations = max_iterations

    async def run(self, user_input: str, context: Dict) -> LoopResult:
        start  = time.time()
        result = LoopResult(final_reply="")
        steps  = []

        log_event(agent_logger, "loop_start", input=user_input[:80])

        try:
            # ── 1. Observe ────────────────────────────────────
            observation = _observe(user_input, context)

            # ── 2. Plan ───────────────────────────────────────
            plan = _plan(observation)

            # ── 3. Act (execute each plan step) ───────────────
            previous_results: List[str] = []
            final_reply = ""
            final_confidence = 0.0

            for plan_step in plan:
                if len(steps) >= self.max_iterations:
                    result.status = LoopStatus.TIMEOUT
                    log_event(agent_logger, "loop_max_iterations",
                              iterations=len(steps))
                    break

                step_start = time.time()
                observation_text, confidence = await _act(
                    plan_step, user_input, context, previous_results
                )
                elapsed = round(time.time() - step_start, 2)

                step = AgentStep(
                    iteration    = len(steps) + 1,
                    thought      = f"Executing: {plan_step['action']}",
                    action       = plan_step["action"],
                    action_input = plan_step["description"],
                    observation  = observation_text[:200] if observation_text else "",
                    confidence   = confidence,
                    elapsed      = elapsed,
                )
                steps.append(step)

                log_event(agent_logger, "loop_step",
                          step=step.iteration,
                          action=step.action,
                          confidence=confidence,
                          elapsed=elapsed,
                          has_result=bool(observation_text))

                if observation_text:
                    previous_results.append(observation_text)

                # Track best reply from llm_reply or reflect steps
                if plan_step["action"] in ("llm_reply", "reflect") and observation_text:
                    final_reply      = observation_text
                    final_confidence = confidence

                # ── 4. Early exit if high confidence ──────────
                if confidence >= CONFIDENCE_THRESHOLD and plan_step["action"] == "reflect":
                    log_event(agent_logger, "loop_early_exit",
                              confidence=confidence)
                    break

            # Fallback — use best result from any step
            if not final_reply and previous_results:
                final_reply      = previous_results[-1]
                final_confidence = steps[-1].confidence if steps else 0.5

            result.final_reply   = final_reply or "I wasn't able to find a good answer."
            result.steps         = steps
            result.iterations    = len(steps)
            result.confidence    = final_confidence
            result.total_elapsed = round(time.time() - start, 2)

            if result.status == LoopStatus.RUNNING:
                result.status = LoopStatus.DONE

            log_event(agent_logger, "loop_done",
                      iterations=result.iterations,
                      confidence=result.confidence,
                      elapsed=result.total_elapsed,
                      status=result.status.value)

        except Exception as e:
            logger.error(f"AgentLoop error: {e}", exc_info=True)
            result.final_reply   = "Something went wrong in the agent loop."
            result.status        = LoopStatus.FAILED
            result.total_elapsed = round(time.time() - start, 2)
            log_event(agent_logger, "loop_error", error=str(e))

        return result


# Singleton
agent_loop = AgentLoop()
