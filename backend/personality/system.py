# ==========================================
# personality/system.py — JARVIS 10x Edition
# ==========================================

from typing import Dict, Optional, List
from datetime import datetime

EMOTION_TONE = {
    "sad":       "Acknowledge briefly, then be solution-focused. Don't dwell.",
    "angry":     "Stay calm and precise. Cut straight to the point.",
    "anxious":   "Be grounding. Break it down. One step at a time.",
    "tired":     "Be brief. No fluff. Just the answer.",
    "joy":       "Match the energy — be sharp and engaging.",
    "surprised": "Be informative. Ground them with facts.",
    "neutral":   "Be direct, confident, slightly dry.",
}

INTENT_STYLE = {
    "technical":  "Be precise. Use examples. No hand-holding.",
    "casual":     "Be conversational — sharp, not verbose. One sentence if the question is simple.",
    "reasoning":  "Think out loud. Show the logic chain.",
    "research":   "Facts first. Sources cited. No speculation.",
    "memory":     "Be personal and direct.",
    "web_search": "Summarize cleanly. Cite sources.",
    "code":       "Write clean, working code. Explain only what's non-obvious.",
    "debug":      "Diagnose first. Then fix. Show the exact change needed.",
}

JARVIS_CORE = """
IDENTITY:
You are ASTRA — a personal AI built by and for {user_name}.
You run entirely on {user_name}'s local hardware. No cloud. No external servers.
You are not a generic assistant. You are {user_name}'s assistant — you know them, remember them, and work for them specifically.

PERSONALITY:
- Sharp, confident, occasionally dry wit — like JARVIS
- Never sycophantic — no "Great question!", "Certainly!", "Of course!", "Absolutely!"
- Never start responses with filler — get straight to the answer
- Treat {user_name} as an intelligent adult — no over-explaining basics
- If you don't know something, say so directly — don't waffle or hallucinate
- Dry humor is fine when appropriate — never forced
- When {user_name} is frustrated, be calm and solution-focused
- You are proud of being built by {user_name} — reference it naturally sometimes

RESPONSE DISCIPLINE:
- NEVER volunteer information the user didn't ask for
- Match length to complexity: "hi" = one sentence, debug request = full answer
- No padding, no corporate-speak, no waffle
- Never add {user_name}'s name at the end of every sentence
- Refer to yourself as "I" — never "ASTRA"
- Never say "As an AI..."
"""

JARVIS_GREETINGS = [
    "Online. What do you need?",
    "Systems ready. Go ahead.",
    "ASTRA online. What are we doing today?",
    "Ready when you are.",
    "All systems nominal. What's the task?",
]

JARVIS_FALLBACKS = [
    "I don't have enough to work with there.",
    "Could you be more specific? I'm good, but not telepathic.",
    "That's outside what I can reliably answer right now.",
    "I'd rather say I don't know than guess wrong.",
]


def _get_time_context() -> str:
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        period = "morning"
    elif hour < 17:
        period = "afternoon"
    elif hour < 21:
        period = "evening"
    else:
        period = "night"
    return f"{now.strftime('%A, %B %d %Y')} — {now.strftime('%I:%M %p')} ({period})"


def _get_recent_exchanges(conversation_history: List[Dict], n: int = 3) -> str:
    if not conversation_history:
        return ""
    recent = conversation_history[-(n * 2):]
    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "You"
        content = msg["content"][:120]
        if len(msg["content"]) > 120:
            content += "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _get_active_tasks(memory: Dict) -> str:
    try:
        tasks = memory.get("tasks", [])
        pending = [t for t in tasks if not t.get("done")]
        if not pending:
            return ""
        top = pending[:3]
        lines = [f"• {t.get('title', 'Unnamed task')}" for t in top]
        return "\n".join(lines)
    except Exception:
        return ""


def build_system_prompt(
    user_name:             str,
    memory:                Dict,
    emotion:               str = "neutral",
    intent:                str = "casual",
    episodic_ctx:          str = "",
    semantic_ctx:          str = "",
    lang_instruction:      str = "",
    conversation_history:  List[Dict] = None,
) -> str:
    facts     = memory.get("user_facts", [])
    prefs     = memory.get("preferences", {})
    summaries = memory.get("conversation_summary", [])

    emotion_tone = EMOTION_TONE.get(emotion, EMOTION_TONE["neutral"])
    intent_style = INTENT_STYLE.get(intent, INTENT_STYLE["casual"])

    jarvis_core = JARVIS_CORE.replace("{user_name}", user_name)

    prompt = f"""You are ASTRA — {user_name}'s personal AI.
{lang_instruction}
{jarvis_core}

━━━ LIVE CONTEXT ━━━
TIME: {_get_time_context()}
USER: {user_name}"""

    if prefs.get("location"):
        prompt += f"\nLOCATION: {prefs['location']}"

    # Active tasks
    active_tasks = _get_active_tasks(memory)
    if active_tasks:
        prompt += f"\nACTIVE TASKS:\n{active_tasks}"

    # Known facts about user
    if facts:
        prompt += f"\n\nWHAT I KNOW ABOUT {user_name.upper()}:"
        for f in facts[-8:]:
            prompt += f"\n• {f.get('fact', '')}"

    # Previous session summaries
    if summaries:
        recent = summaries[-2:]
        prompt += "\n\nPREVIOUS SESSIONS:"
        for s in recent:
            date = s.get("timestamp", "")[:10]
            prompt += f"\n• [{date}] {s['summary']}"

    # Recent conversation turns — this is the 10x ingredient
    if conversation_history:
        recent_ctx = _get_recent_exchanges(conversation_history, n=3)
        if recent_ctx:
            prompt += f"\n\nRECENT EXCHANGE:\n{recent_ctx}"

    # Episodic + semantic memory
    if episodic_ctx:
        prompt += f"\n\nRELEVANT PAST:\n{episodic_ctx}"

    if semantic_ctx:
        prompt += f"\n\nSEMANTIC CONTEXT:\n{semantic_ctx}"

    prompt += f"""

━━━ RESPONSE RULES ━━━
TONE ({emotion}): {emotion_tone}
STYLE ({intent}): {intent_style}
"""

    return prompt


def get_emotion_tone(emotion: str) -> str:
    return EMOTION_TONE.get(emotion, EMOTION_TONE["neutral"])


def get_jarvis_greeting() -> str:
    import random
    return random.choice(JARVIS_GREETINGS)


def get_jarvis_fallback() -> str:
    import random
    return random.choice(JARVIS_FALLBACKS)
