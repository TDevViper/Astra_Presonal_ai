# ==========================================
# api/digest.py — Daily Digest endpoint
# ==========================================
import logging
from datetime import datetime
from flask import Blueprint, jsonify

logger   = logging.getLogger(__name__)
digest_bp = Blueprint("digest_api", __name__)


@digest_bp.route("/api/digest", methods=["GET"])
def get_digest():
    try:
        from memory.memory_engine import load_memory
        from memory.episodic import _load_episodes, get_episode_stats
        from core.proactive import analyze_patterns, get_session_summary
        from briefing import generate_morning_brief

        memory    = load_memory()
        user_name = memory.get("preferences", {}).get("name", "User")
        today     = datetime.now().strftime("%Y-%m-%d")
        now       = datetime.now()

        # ── Today's episodes ────────────────────────────────────────
        all_episodes = _load_episodes()
        today_eps    = [e for e in all_episodes if e.get("date") == today]

        # ── Conversation summary (LLM if episodes exist) ─────────────
        conv_summary = ""
        if today_eps:
            try:
                from memory.summarizer import summarize_conversation
                # Build fake history from today's episodes for summarizer
                fake_history = []
                for ep in today_eps[-10:]:
                    fake_history.append({"role": "user",      "content": ep["user"]})
                    fake_history.append({"role": "assistant", "content": ep["astra"]})
                conv_summary = summarize_conversation(fake_history, memory, user_name)
            except Exception as e:
                logger.warning("Summarization skipped: %s", e)
                # Fallback: list top intents
                from collections import Counter
                intents = Counter(e.get("intent","") for e in today_eps if e.get("intent"))
                top     = [i for i, _ in intents.most_common(3) if i]
                conv_summary = f"Today's main activities: {', '.join(top)}." if top else ""

        # ── Patterns (top topics across all time) ────────────────────
        patterns   = analyze_patterns()
        top_topics = patterns.get("top_topics", [])

        # ── Pending tasks ────────────────────────────────────────────
        tasks   = memory.get("tasks", [])
        pending = [t for t in tasks if t.get("status") == "todo"]

        # ── Episode stats ─────────────────────────────────────────────
        stats = get_episode_stats()

        # ── Greeting ─────────────────────────────────────────────────
        hour = now.hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        # ── Assemble digest text ──────────────────────────────────────
        lines = [f"{greeting}, {user_name}! Here's your daily digest."]
        lines.append(f"📅 {now.strftime('%A, %B %d, %Y')}")

        if today_eps:
            lines.append(f"\n💬 Today's sessions: {len(today_eps)} exchanges.")
        if conv_summary:
            lines.append(f"📝 {conv_summary}")

        if pending:
            task_titles = ", ".join(t.get("title", "untitled") for t in pending[:3])
            lines.append(f"\n📌 Pending tasks ({len(pending)}): {task_titles}.")

        if top_topics:
            lines.append(f"\n🔍 Your most discussed topics: {', '.join(top_topics[:3])}.")

        lines.append(f"\n📊 Total conversations stored: {stats.get('total', 0)}.")

        digest_text = "\n".join(lines)

        return jsonify({
            "digest":        digest_text,
            "user_name":     user_name,
            "date":          today,
            "today_exchanges": len(today_eps),
            "pending_tasks": len(pending),
            "top_topics":    top_topics[:5],
            "summary":       conv_summary,
            "stats":         stats,
        })

    except Exception as e:
        logger.error("Digest error: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500
