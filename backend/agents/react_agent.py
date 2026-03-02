# ==========================================
# agents/react_agent.py — v2.0 (Real ReAct)
# ==========================================

import logging
import ollama
from typing import Dict, List

logger = logging.getLogger(__name__)

MAX_STEPS  = 3
MAX_TOKENS = 400

_REACT_TRIGGERS = [
    "why", "how does", "step by step", "walk me through",
    "break down", "reason", "analyze", "explain how",
    "what would happen if", "should i", "compare", "pros and cons"
]


def needs_react(user_input: str) -> bool:
    t = user_input.lower()
    return any(trigger in t for trigger in _REACT_TRIGGERS)


def react_solve(user_input: str, model: str = "mistral:latest",
                context: str = "", user_name: str = "Arnav") -> Dict:
    logger.info(f"⚛️  ReAct loop starting: {user_input[:60]}...")

    system_prompt = f"""You are ASTRA, {user_name}'s AI assistant.
Solve problems step by step using this format:

Thought: [what you are thinking]
Action: [what you are doing — analyze/recall/calculate/conclude]
Observation: [what you found]

After reasoning, end with:
Final Answer: [clear, direct answer]

Be concise. Max {MAX_STEPS} thought cycles.
{f"Context about {user_name}: {context}" if context else ""}"""

    messages: List[Dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_input}
    ]

    steps    = []
    full_out = ""

    try:
        for step in range(MAX_STEPS):
            response = ollama.chat(
                model=model,
                messages=messages,
                options={"temperature": 0.4, "num_predict": MAX_TOKENS}
            )
            output = response["message"]["content"].strip()
            full_out += output + "\n"

            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("Thought:"):
                    steps.append({"type": "thought", "content": line[8:].strip()})
                elif line.startswith("Action:"):
                    steps.append({"type": "action",  "content": line[7:].strip()})
                elif line.startswith("Observation:"):
                    steps.append({"type": "observe",  "content": line[12:].strip()})

            if "Final Answer:" in output:
                break

            messages.append({"role": "assistant", "content": output})
            messages.append({"role": "user",      "content": "Continue your reasoning."})

        if "Final Answer:" in full_out:
            final = full_out.split("Final Answer:")[-1].strip()
            final = final.split("\n\n")[0].strip()
        else:
            lines = [l.strip() for l in full_out.split("\n") if l.strip()
                     and not any(l.startswith(p) for p in ["Thought:", "Action:", "Observation:"])]
            final = lines[-1] if lines else full_out.strip()

        # Build rich answer with reasoning steps visible
        reasoning_lines = []
        for s in steps:
            if s["type"] == "thought":
                reasoning_lines.append(f"💭 {s['content']}")
            elif s["type"] == "action":
                reasoning_lines.append(f"⚡ {s['content']}")
            elif s["type"] == "observe":
                reasoning_lines.append(f"👁 {s['content']}")

        if reasoning_lines:
            answer = "\n".join(reasoning_lines) + "\n\n" + final
        else:
            answer = final

        logger.info(f"✅ ReAct done — {len(steps)} steps")
        return {"answer": answer, "steps": steps, "success": True}

    except Exception as e:
        logger.error(f"❌ ReAct failed: {e}")
        return {"answer": "", "steps": [], "success": False}


def react(user_input: str, model: str = "mistral:latest",
          context: str = "", user_name: str = "Arnav") -> str:
    if not needs_react(user_input):
        return ""
    print(f"[REACT] Triggered for: {user_input[:50]}", flush=True)
    result = react_solve(user_input, model=model,
                         context=context, user_name=user_name)
    return result["answer"] if result["success"] else ""
