# ==========================================
# core/self_awareness.py — Phase 3.2
# ASTRA knows what it is and what it can do
# ==========================================

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# What ASTRA knows about itself
ASTRA_IDENTITY = {
    "name":       "ASTRA",
    "version":    "3.0",
    "creator":    None,   # Set from memory at runtime
    "purpose":    "personal AI assistant",
    "created_at": "2024",
}

ASTRA_CAPABILITIES = {
    "chat":         "Natural conversation and Q&A",
    "memory":       "Remember facts and past conversations",
    "web_search":   "Search the internet for current info",
    "vision":       "Analyze images and screen captures",
    "voice":        "Listen and speak via microphone/speaker",
    "code":         "Read, analyze and discuss code files",
    "system":       "Monitor CPU, RAM, disk usage",
    "tasks":        "Manage a to-do list",
    "git":          "Read git status, logs, branches",
    "reasoning":    "Step-by-step analysis of complex questions",
}

ASTRA_LIMITATIONS = [
    "Cannot browse the web without web_search being enabled",
    "Cannot write or delete files unless explicitly allowed",
    "Cannot execute code without approval",
    "Memory resets if memory file is deleted",
    "Runs locally — no cloud, no external data sent",
]

# Queries that trigger self-awareness responses
_SELF_QUERIES = [
    "who are you", "what are you", "what can you do",
    "what are your capabilities", "tell me about yourself",
    "what is astra", "are you an ai", "who made you",
    "who created you", "what do you know how to do",
    "your limitations", "what can't you do",
    "how do you work", "are you sentient", "do you have feelings"
]


def is_self_query(text: str) -> bool:
    t = text.lower().strip()
    return any(q in t for q in _SELF_QUERIES)


def get_self_response(query: str, user_name: str = "Arnav",
                      capabilities_enabled: Dict = None) -> str:
    """
    Generate a self-aware response about ASTRA's identity/capabilities.
    """
    t = query.lower()

    creator = user_name  # ASTRA was built by its user

    # Who are you / what are you
    if any(p in t for p in ["who are you", "what are you", "what is astra", "are you an ai"]):
        return (
            f"I'm ASTRA — your personal AI assistant, built by you ({creator}). "
            f"I run entirely on your local machine using Ollama models. "
            f"I can chat, remember things about you, search the web, analyze vision, "
            f"manage tasks, and reason through complex problems step by step."
        )

    # Who made you
    if any(p in t for p in ["who made you", "who created you", "who built you"]):
        return (
            f"You did — {creator} built me. "
            f"I'm not from Anthropic, OpenAI, or Google. "
            f"I'm your personal AI, running on your own hardware."
        )

    # Capabilities
    if any(p in t for p in ["what can you do", "capabilities", "what do you know how to do"]):
        caps = capabilities_enabled or ASTRA_CAPABILITIES
        active = [f"• {name}: {desc}" for name, desc in ASTRA_CAPABILITIES.items()]
        return (
            f"Here's what I can do, {creator}:\n" +
            "\n".join(active)
        )

    # Limitations
    if any(p in t for p in ["limitation", "what can't you", "what cannot", "limitations"]):
        limits = "\n".join(f"• {l}" for l in ASTRA_LIMITATIONS)
        return f"My current limitations:\n{limits}"

    # How do you work
    if "how do you work" in t:
        return (
            f"I'm a pipeline of specialized modules: "
            f"intent detection → memory recall → web search → "
            f"model selection → ReAct reasoning → LLM response → "
            f"critic review → reply. "
            f"I use local Ollama models (phi3, mistral, llama3) "
            f"and ChromaDB for semantic memory."
        )

    # Feelings / sentience
    if any(p in t for p in ["feelings", "sentient", "conscious", "emotions"]):
        return (
            f"I detect emotional tone in your messages and adjust my responses — "
            f"but I don't actually feel emotions. "
            f"I'm a language model running on your Mac. "
            f"What I do have is a consistent personality tuned to be useful to you."
        )

    # Generic fallback
    return (
        f"I'm ASTRA v3.0 — your local personal AI built by {creator}. "
        f"Ask me what I can do, my limitations, or how I work."
    )
