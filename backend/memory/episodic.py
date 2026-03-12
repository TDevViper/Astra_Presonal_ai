# ==========================================
# memory/episodic.py — Phase 3.1
# ASTRA remembers past conversations
# ==========================================

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

_BACKEND_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPISODES_FILE = os.path.join(_BACKEND_DIR, "memory", "data", "episodes.json")

MAX_EPISODES = 100  # Keep last 100 conversation episodes


def _load_episodes() -> List[Dict]:
    if not os.path.exists(EPISODES_FILE):
        return []
    try:
        with open(EPISODES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_episodes(episodes: List[Dict]) -> None:
    os.makedirs(os.path.dirname(EPISODES_FILE), exist_ok=True)
    with open(EPISODES_FILE, "w") as f:
        json.dump(episodes[-MAX_EPISODES:], f, indent=2)


def store_episode(user_msg: str, astra_reply: str,
                  intent: str = "", emotion: str = "",
                  user_name: str = "Arnav") -> None:
    """
    Store one conversation turn as an episode.
    Called after every successful response.
    """
    episodes = _load_episodes()
    episodes.append({
        "timestamp":  datetime.utcnow().isoformat(),
        "date":       datetime.utcnow().strftime("%Y-%m-%d"),
        "user":       user_msg[:300],
        "astra":      astra_reply[:300],
        "intent":     intent,
        "emotion":    emotion,
        "user_name":  user_name
    })
    _auto_extract_after_store(user_msg, astra_reply) 
    _save_episodes(episodes)
    logger.debug(f"📼 Episode stored: {user_msg[:40]}")
    try:
        from knowledge.entity_extractor import extract_and_store
        extract_and_store(user_msg + " " + astra_reply, user_name=user_name)
    except Exception:
        pass  # TODO: handle


def recall_episodes(query: str, top_k: int = 3) -> List[Dict]:
    """
    Find past episodes relevant to current query.
    Simple keyword overlap — no embedding needed.
    """
    episodes = _load_episodes()
    if not episodes:
        return []

    query_words = set(query.lower().split())
    # Remove stop words
    stop = {"i", "a", "the", "is", "are", "was", "what", "how",
            "why", "do", "did", "can", "you", "me", "my", "about"}
    query_words -= stop

    if not query_words:
        return []

    scored = []
    for ep in episodes:
        ep_text  = (ep["user"] + " " + ep["astra"]).lower()
        ep_words = set(ep_text.split())
        overlap  = len(query_words & ep_words)
        if overlap > 0:
            scored.append((overlap, ep))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [ep for _, ep in scored[:top_k]]


def build_episodic_context(query: str, user_name: str = "Arnav") -> str:
    """
    Build a context string from past episodes to inject into system prompt.
    Makes ASTRA feel like it 'remembers' past conversations.
    """
    episodes = recall_episodes(query, top_k=3)
    if not episodes:
        return ""

    lines = [f"\nWhat {user_name} and I discussed before (relevant to now):"]
    for ep in episodes:
        date  = ep.get("date", "recently")
        user  = ep["user"][:80]
        astra = ep["astra"][:80]
        lines.append(f"• [{date}] {user_name} asked: \"{user}\" → I said: \"{astra}\"")

    context = "\n".join(lines)
    logger.info(f"📼 Episodic context built — {len(episodes)} past episodes recalled")
    return context


def get_episode_stats() -> Dict:
    episodes = _load_episodes()
    if not episodes:
        return {"total": 0, "oldest": None, "newest": None}
    return {
        "total":   len(episodes),
        "oldest":  episodes[0]["date"] if episodes else None,
        "newest":  episodes[-1]["date"] if episodes else None,
    }

# ── Auto knowledge graph population (appended by upgrade) ──────────────
def _auto_extract_after_store(user_msg: str, reply: str):
    try:
        from knowledge.auto_extractor import extract_and_store
        extract_and_store(user_msg + " " + reply, user_name="Arnav")
    except Exception:
        pass  # TODO: handle
