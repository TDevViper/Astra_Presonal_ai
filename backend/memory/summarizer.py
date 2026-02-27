# ==========================================
# astra_engine/memory/summarizer.py  (NEW)
# ==========================================

import logging
import ollama
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


def should_summarize(conversation_history: List[Dict]) -> bool:
    """Trigger summarization every 10 messages."""
    return len(conversation_history) >= 10 and len(conversation_history) % 10 == 0


def summarize_conversation(
    history: List[Dict],
    memory: Dict,
    user_name: str,
    model: str = "phi3:mini"
) -> str:
    """
    Use LLM to summarize recent conversation into 2-3 sentences.
    Stores summary in memory["conversation_summary"].
    Returns summary string.
    """
    if not history:
        return ""

    # Format last 10 messages
    recent = history[-10:]
    formatted = "\n".join([
        f"{m['role'].upper()}: {m['content'][:100]}"
        for m in recent
    ])

    prompt = f"""Summarize this conversation between {user_name} and ASTRA in 2-3 sentences.
Focus on: what {user_name} asked about, what topics were discussed, any decisions made.
Be factual and concise. No fluff.

Conversation:
{formatted}

Summary:"""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_predict": 150}
        )
        summary = response["message"]["content"].strip()
        logger.info(f"📝 Generated summary: {summary[:80]}...")
        return summary

    except Exception as e:
        logger.error(f"❌ Summarization failed: {e}")
        # Fallback: basic keyword summary
        topics = set()
        for m in recent:
            if m["role"] == "user":
                words = m["content"].lower().split()
                for w in words:
                    if len(w) > 5:
                        topics.add(w)
        return f"{user_name} discussed: {', '.join(list(topics)[:5])}."


def store_summary(memory: Dict, summary: str) -> Dict:
    """Add summary to memory's conversation_summary list."""
    if "conversation_summary" not in memory:
        memory["conversation_summary"] = []

    memory["conversation_summary"].append({
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat(),
        "message_count": len(memory.get("conversation_summary", [])) * 10 + 10
    })

    # Keep only last 10 summaries
    if len(memory["conversation_summary"]) > 10:
        memory["conversation_summary"] = memory["conversation_summary"][-10:]

    logger.info(f"💾 Stored summary #{len(memory['conversation_summary'])}")
    return memory


def get_recent_context(memory: Dict, max_summaries: int = 3) -> str:
    """
    Get recent conversation summaries as context string for LLM.
    Injected into system prompt for long-term memory.
    """
    summaries = memory.get("conversation_summary", [])
    if not summaries:
        return ""

    recent = summaries[-max_summaries:]
    context = "\nPREVIOUS CONVERSATION CONTEXT:\n"
    for s in recent:
        ts = s.get("timestamp", "")[:10]  # Just date
        context += f"• [{ts}] {s['summary']}\n"

    return context