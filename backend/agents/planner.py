# ==========================================
# agents/planner.py
# Task decomposer for multi-step queries
# "Research X and summarize" → [search, read, summarize]
# ==========================================

import logging
import ollama
import os
from typing import List, Dict

logger = logging.getLogger(__name__)

GPU_HOST   = "http://100.113.54.3:11434"
LOCAL_HOST = "http://localhost:11434"

# Queries that need planning (multi-step)
PLAN_TRIGGERS = [
    "research and", "find and", "search and summarize",
    "look up and", "compare and", "analyze and",
    "first", "then", "after that", "step by step",
    "plan for", "how do i", "walk me through"
]


def needs_planning(text: str) -> bool:
    t = text.lower()
    return any(trigger in t for trigger in PLAN_TRIGGERS)


def decompose(user_input: str) -> List[Dict]:
    """
    Break complex task into steps.
    Returns list of {step, action, tool} dicts.
    """
    try:
        import requests
        r = requests.get(GPU_HOST, timeout=1)
        host  = GPU_HOST if r.status_code == 200 else LOCAL_HOST
    except Exception:
        host  = LOCAL_HOST

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
            model="mistral:latest",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_predict": 150}
        )
        raw    = response["message"]["content"].strip()
        steps  = []
        import re
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Parse "1. [action] description"
            m = re.match(r'\d+\.\s+\[(\w+)\]\s+(.*)', line)
            if m:
                steps.append({"step": len(steps)+1, "action": m.group(1), "description": m.group(2)})
            elif re.match(r'\d+\.', line):
                desc = re.sub(r'^\d+\.\s*', '', line)
                steps.append({"step": len(steps)+1, "action": "answer_directly", "description": desc})

        logger.info(f"📋 Plan: {steps}")
        return steps

    except Exception as e:
        logger.warning(f"Planner failed: {e}")
        return [{"step": 1, "action": "answer_directly", "description": user_input}]


def execute_plan(steps: List[Dict], user_input: str) -> str:
    """Execute each step and combine results."""
    results = []

    for step in steps:
        action = step.get("action", "answer_directly")
        desc   = step.get("description", "")

        try:
            if action == "web_search":
                from tools.web_search import handle_search_command
                r = handle_search_command(desc or user_input)
                if r:
                    results.append(f"Search: {r[:300]}")

            elif action == "recall_memory":
                from memory.memory_recall import memory_recall
                from memory.memory_engine import load_memory
                r = memory_recall(desc, load_memory(), "Arnav")
                if r:
                    results.append(f"Memory: {r}")

            elif action == "summarize" and results:
                results.append(f"Summary of above: see below")

            else:
                results.append(desc)

        except Exception as e:
            logger.warning(f"Step {step['step']} failed: {e}")

    return "\n\n".join(results) if results else ""
