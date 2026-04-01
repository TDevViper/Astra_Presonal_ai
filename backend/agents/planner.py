import logging
import re
import os
import ollama
from typing import List, Dict

logger = logging.getLogger(__name__)

GPU_HOST = os.getenv("REMOTE_GPU_HOST", "")
LOCAL_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
ASTRA_MODEL = os.getenv("ASTRA_MODEL", "phi3:mini")

PLAN_TRIGGERS = [
    "research and",
    "find and",
    "search and summarize",
    "look up and",
    "compare and",
    "analyze and",
    "first",
    "then",
    "after that",
    "step by step",
    "plan for",
    "how do i",
    "walk me through",
]


def _get_host() -> str:
    if not GPU_HOST:
        return LOCAL_HOST
    try:
        import requests

        r = requests.get(GPU_HOST, timeout=1)
        return GPU_HOST if r.status_code == 200 else LOCAL_HOST
    except Exception:
        return LOCAL_HOST


def needs_planning(text: str) -> bool:
    return any(trigger in text.lower() for trigger in PLAN_TRIGGERS)


def decompose(user_input: str) -> List[Dict]:
    host = _get_host()
    client = ollama.Client(host=host)
    prompt = f"""You are a task planner for an AI assistant.
Break this request into clear steps (max 4).
Available actions: web_search, summarize, calculate, recall_memory, answer_directly
Output ONLY a numbered list like:
1. [action] description
2. [action] description

Request: {user_input}
Steps:"""
    try:
        response = client.chat(
            model=ASTRA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_predict": 150},
        )
        raw = response["message"]["content"].strip()
        steps = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"\d+\.\s+\[(\w+)\]\s+(.*)", line)
            if m:
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": m.group(1),
                        "description": m.group(2),
                    }
                )
            elif re.match(r"\d+\.", line):
                desc = re.sub(r"^\d+\.\s*", "", line)
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "action": "answer_directly",
                        "description": desc,
                    }
                )
        logger.info(f"📋 Plan: {steps}")
        return steps
    except Exception as e:
        if "Connection refused" in str(e) or "Errno 61" in str(e):
            logger.error("Ollama not running — run: ollama serve")
        else:
            logger.warning(f"Planner failed: {e}")
        return [{"step": 1, "action": "answer_directly", "description": user_input}]


def execute_plan(steps: List[Dict], user_input: str) -> str:
    results = []
    for step in steps:
        action = step.get("action", "answer_directly")
        desc = step.get("description", "")
        try:
            if action == "web_search":
                from tools.web_search import handle_search_command

                r = handle_search_command(desc or user_input)
                if r:
                    results.append(f"Search: {r[:300]}")
            elif action == "recall_memory":
                from memory.memory_recall import memory_recall
                from memory.memory_engine import load_memory

                mem_pl = load_memory()
                r = memory_recall(
                    desc, mem_pl, mem_pl.get("preferences", {}).get("name", "User")
                )
                if r:
                    results.append(f"Memory: {r}")
            elif action == "summarize" and results:
                results.append("Summary of above: see below")
            else:
                results.append(desc)
        except Exception as e:
            logger.warning(f"Step {step['step']} failed: {e}")
    return "\n\n".join(results) if results else ""
