# ==========================================
# core/proactive.py — Phase 4
# ASTRA notices patterns and gives suggestions
# ==========================================

import json
import os
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from collections import Counter

logger = logging.getLogger(__name__)

_BACKEND_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPISODES_FILE  = os.path.join(_BACKEND_DIR, "memory", "data", "episodes.json")
PATTERNS_FILE  = os.path.join(_BACKEND_DIR, "memory", "data", "patterns.json")


# ── Load helpers ──────────────────────────────────────────────

def _load_episodes() -> List[Dict]:
    if not os.path.exists(EPISODES_FILE):
        return []
    try:
        with open(EPISODES_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _load_patterns() -> Dict:
    if not os.path.exists(PATTERNS_FILE):
        return {"topics": {}, "last_session": None, "pending_tasks": []}
    try:
        with open(PATTERNS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"topics": {}, "last_session": None, "pending_tasks": []}


def _save_patterns(patterns: Dict) -> None:
    os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)
    with open(PATTERNS_FILE, "w") as f:
        json.dump(patterns, f, indent=2)


# ── Pattern Analysis ──────────────────────────────────────────

def analyze_patterns() -> Dict:
    """
    Analyze episode history to find:
    - Most discussed topics
    - Frequent intents
    - Last session summary
    """
    episodes = _load_episodes()
    if not episodes:
        return {}

    # Count topic words from user messages
    stop_words = {
        "i", "a", "the", "is", "are", "was", "what", "how", "why",
        "do", "did", "can", "you", "me", "my", "about", "to", "in",
        "of", "and", "or", "for", "with", "it", "this", "that", "be",
        "explain", "tell", "show", "give", "make", "help", "please",
        "would", "could", "should", "does", "have", "has", "will",
        "want", "need", "think", "know", "understand", "using", "use"
    }

    word_counts: Counter = Counter()
    intent_counts: Counter = Counter()

    for ep in episodes[-50:]:  # Last 50 episodes
        words = ep.get("user", "").lower().split()
        for w in words:
            w = w.strip(".,?!")
            if len(w) > 4 and w not in stop_words:
                word_counts[w] += 1
        if ep.get("intent"):
            intent_counts[ep["intent"]] += 1

    top_topics  = [w for w, _ in word_counts.most_common(5)]
    top_intents = [i for i, _ in intent_counts.most_common(3)]

    patterns = _load_patterns()
    patterns["topics"]       = dict(word_counts.most_common(10))
    patterns["top_topics"]   = top_topics
    patterns["top_intents"]  = top_intents
    patterns["last_session"] = datetime.utcnow().isoformat()
    patterns["episode_count"] = len(episodes)
    _save_patterns(patterns)

    return patterns


# ── Welcome Back Message ───────────────────────────────────────

def get_welcome_back(user_name: str = "Arnav") -> Optional[str]:
    """
    Generate a context-aware greeting when ASTRA starts.
    References what was discussed last time.
    """
    episodes = _load_episodes()
    if not episodes:
        return None

    # Get last few episodes
    last = episodes[-3:]
    today = date.today().isoformat()

    # Check if last session was today
    last_date = last[-1].get("date", "")
    if last_date == today:
        return None  # Same day — no welcome back needed

    # Build welcome with context
    topics = []
    for ep in reversed(last):
        user_msg = ep.get("user", "")
        if len(user_msg) > 10:
            # Extract key noun (simple: longest word)
            words = [w for w in user_msg.split() if len(w) > 5]
            if words:
                topics.append(words[0])

    topics = list(dict.fromkeys(topics))[:2]  # Dedupe, max 2

    if topics:
        topic_str = " and ".join(topics)
        return (
            f"Welcome back, {user_name}! "
            f"Last time we were discussing {topic_str}. "
            f"Want to continue, or something new today?"
        )

    return f"Welcome back, {user_name}! What are we working on today?"


# ── Proactive Suggestions ─────────────────────────────────────

def get_proactive_suggestion(user_input: str, memory: Dict,
                              user_name: str = "Arnav") -> Optional[str]:
    """
    Analyze current message + history to offer unsolicited helpful suggestions.
    Returns suggestion string or None.
    """
    patterns = analyze_patterns()
    top_topics = patterns.get("top_topics", [])
    t = user_input.lower()

    # ── Suggestion 1: Repeated topic pattern ─────────────────
    # If user asks about same topic 3+ times, suggest deeper resource
    topic_counts = patterns.get("topics", {})
    for word in user_input.lower().split():
        if len(word) > 5 and topic_counts.get(word, 0) >= 3:
            return (
                f"💡 I've noticed you ask about '{word}' often. "
                f"Want me to build a summary or learning path for it?"
            )

    # ── Suggestion 2: Coding + no git ────────────────────────
    if any(w in t for w in ["code", "function", "class", "bug", "error"]):
        episodes = _load_episodes()
        recent_intents = [e.get("intent") for e in episodes[-10:]]
        if "git_operation" not in recent_intents:
            return "💡 Working on code? I can check your git status if you want."

    # ── Suggestion 3: Pending tasks reminder ─────────────────
    tasks = memory.get("tasks", [])
    if tasks:
        pending = [t for t in tasks if t.get("status") == "todo"]
        if pending and len(pending) >= 2:
            return (
                f"💡 You have {len(pending)} pending tasks. "
                f"Want to review them?"
            )

    # ── Suggestion 4: Long session without break ─────────────
    episodes = _load_episodes()
    today_eps = [e for e in episodes if e.get("date") == date.today().isoformat()]
    if len(today_eps) >= 20:
        return "💡 You've been at this for a while. Take a break?"

    return None


# ── Session Summary ───────────────────────────────────────────

def get_session_summary(user_name: str = "Arnav") -> Optional[str]:
    """
    At end of session (when user says bye/exit),
    summarize what was accomplished.
    """
    episodes = _load_episodes()
    today = date.today().isoformat()
    today_eps = [e for e in episodes if e.get("date") == today]

    if not today_eps:
        return None

    intents = Counter(e.get("intent", "") for e in today_eps)
    top = [i for i, _ in intents.most_common(3) if i]

    return (
        f"Today's session: {len(today_eps)} exchanges. "
        f"Main activities: {', '.join(top) if top else 'general chat'}. "
        f"Good work, {user_name}!"
    )
