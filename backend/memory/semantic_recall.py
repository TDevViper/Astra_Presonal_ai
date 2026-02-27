# ==========================================
# memory/semantic_recall.py - v3
# Structured injection + confidence boost
# ==========================================

import logging
from typing import Dict, Optional, Tuple

from memory.vector_store import semantic_search, store_fact, store_exchange

logger = logging.getLogger(__name__)

CONFIDENCE_BOOST_THRESHOLD = 0.70   # Priority 4: boost confidence if hit >= this
BOOSTED_CONFIDENCE         = 0.85


def build_semantic_context(query: str, user_name: str = "user") -> Tuple[str, float]:
    """
    Run semantic search and return:
      - structured context string to inject into LLM system prompt
      - confidence boost value (0.0 if no strong hit)

    Priority 7: structured injection format so LLM reads it clearly.
    Priority 3: only injects above threshold (handled in vector_store).
    Priority 4: returns confidence boost if strong match found.
    Priority 5: facts listed first, exchanges second.
    """
    facts, exchanges = semantic_search(query)
    confidence_boost = 0.0

    if not facts and not exchanges:
        return "", 0.0

    lines = [f"\nRelevant facts about {user_name}:"]

    # ── Facts first (highest priority) ───────────────────────
    for hit in facts[:3]:
        lines.append(f"- {hit['text']}")
        logger.info(
            f"🧠 semantic_hit | source=fact score={hit['score']} "
            f"text='{hit['text'][:60]}'"
        )
        if hit["score"] >= CONFIDENCE_BOOST_THRESHOLD:
            confidence_boost = BOOSTED_CONFIDENCE

    # ── Exchanges as supporting context (lower priority) ─────
    if exchanges:
        lines.append(f"\nRecent relevant context:")
        for hit in exchanges[:2]:
            lines.append(f"- {hit['text'][:120]}")
            logger.info(
                f"🧠 semantic_hit | source=exchange score={hit['score']} "
                f"text='{hit['text'][:60]}'"
            )

    context = "\n".join(lines)
    return context, confidence_boost


def index_user_fact(fact_dict: Dict, user_name: str = "user") -> None:
    """Index a newly extracted user fact into vector memory."""
    fact_text = fact_dict.get("fact", "")
    fact_type = fact_dict.get("type", "fact")

    if fact_text:
        success = store_fact(fact_text, fact_type=fact_type, user_name=user_name)
        if success:
            logger.info(f"📥 indexed_fact | text='{fact_text[:60]}'")


def index_exchange(user_msg: str, assistant_reply: str, user_name: str = "user") -> None:
    """Index a conversation exchange — only if both sides are substantive."""
    if len(user_msg.strip()) > 20 and len(assistant_reply.strip()) > 20:
        store_exchange(user_msg, assistant_reply, user_name=user_name)
        logger.info(f"📥 indexed_exchange | user='{user_msg[:40]}'")