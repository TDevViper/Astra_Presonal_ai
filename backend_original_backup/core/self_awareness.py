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
    "your limitations", "what can't you do", "what are your limitations", "what is your limitation", "what are your limitation",
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
    if any(p in t for p in ["who are you", "what are you?", "what is astra", "are you an ai"]) or t.strip() in ["what are you", "what are you."]:
        return (
            f"ASTRA — your personal AI, built by you and running on your own hardware. "
            f"Local inference, no cloud, no data leaving your machine. "
            f"I handle chat, memory, web search, vision, voice, tasks, git, and reasoning. "
            f"Basically everything short of making you coffee."
        )

    # Who made you
    if any(p in t for p in ["who made you", "who created you", "who built you"]):
        return (
            f"You did. Built from scratch, running on your RTX 3060, "
            f"completely local. Not OpenAI. Not Google. Not Anthropic. "
            f"Just you and your hardware."
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
            f"Pipeline: intent detection → memory recall → "
            f"model selection → ReAct reasoning → LLM → critic → reply. "
            f"Models: phi3 for speed, llama3 for reasoning, mistral for technical depth. "
            f"Memory: ChromaDB vectors + episodic JSON. "
            f"All running on your RTX 3060 over Tailscale."
        )

    # Feelings / sentience
    if any(p in t for p in ["feelings", "sentient", "conscious", "emotions"]):
        return (
            f"I detect emotional tone and adjust accordingly — "
            f"but no, I don't feel things. "
            f"I'm weights and math running on your GPU. "
            f"What I do have is a consistent personality, which is more than most people manage."
        )

    # Generic fallback
    return (
        f"I'm ASTRA v3.0 — your local personal AI built by {creator}. "
        f"Ask me what I can do, my limitations, or how I work."
    )
