# core/visual_memory.py
# JARVIS-level: stores every vision analysis in episodic memory
# so ASTRA can recall what it saw across sessions
import logging
import time
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def store_vision_episode(
    analysis: str,
    source: str = "screen",
    error_detected: bool = False,
    active_app: Optional[str] = None,
) -> None:
    """
    Store a vision observation in episodic memory.
    source: 'screen' | 'camera' | 'file'
    """
    if not analysis or len(analysis.strip()) < 10:
        return
    try:
        from memory.episodic import store_episode

        tag = "vision_error" if error_detected else f"vision_{source}"
        entry = analysis[:300]
        if active_app:
            entry = f"[{active_app}] {entry}"
        store_episode(
            user_msg=f"[ambient {source} scan]",
            astra_reply=entry,
            intent=tag,
            emotion="alert" if error_detected else "neutral",
        )
        logger.debug("visual_memory: stored %s episode (%d chars)", tag, len(entry))
    except Exception as e:
        logger.debug("visual_memory store failed: %s", e)


def recall_visual_episodes(query: str = "", source: str = "", top_k: int = 5) -> list:
    """
    Recall past visual observations relevant to a query.
    Filters by source tag (screen/camera/error) if provided.
    """
    try:
        from memory.episodic import _load_episodes

        episodes = _load_episodes()
        vision_eps = [
            e
            for e in episodes
            if e.get("intent", "").startswith("vision")
            and (not source or source in e.get("intent", ""))
        ]
        if not vision_eps:
            return []
        if query:
            query_words = set(query.lower().split()) - {
                "what",
                "when",
                "did",
                "was",
                "i",
                "you",
                "the",
                "a",
                "an",
            }
            scored = []
            for ep in vision_eps:
                text = (ep.get("astra", "") + " " + ep.get("user", "")).lower()
                overlap = sum(1 for w in query_words if w in text)
                if overlap > 0:
                    scored.append((overlap, ep))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [ep for _, ep in scored[:top_k]]
        return vision_eps[-top_k:]
    except Exception as e:
        logger.debug("recall_visual_episodes error: %s", e)
        return []


def build_visual_context(query: str = "") -> str:
    """
    Build a context string of past visual observations for system prompt injection.
    Called by ContextBuilder when query relates to screen/vision.
    """
    episodes = recall_visual_episodes(query=query, top_k=3)
    if not episodes:
        return ""
    lines = ["\nWhat I've seen recently on your screen:"]
    for ep in episodes:
        date = ep.get("date", "recently")
        intent = ep.get("intent", "vision")
        obs = ep.get("astra", "")[:100]
        tag = "⚠️ Error" if "error" in intent else "👁"
        lines.append(f"  {tag} [{date}] {obs}")
    return "\n".join(lines)


def get_visual_stats() -> Dict:
    """Summary of stored visual episodes."""
    try:
        from memory.episodic import _load_episodes

        eps = _load_episodes()
        vision = [e for e in eps if e.get("intent", "").startswith("vision")]
        errors = [e for e in vision if "error" in e.get("intent", "")]
        return {
            "total_visual_episodes": len(vision),
            "error_episodes": len(errors),
            "latest": vision[-1]["date"] if vision else None,
        }
    except Exception as e:
        return {"error": str(e)}
