"""
core/feedback.py — User feedback loop for ASTRA.

Stores thumbs up/down ratings against message IDs.
Writes a JSONL fine-tuning dataset that can feed future model training.
Low ratings immediately trigger deep LLM scoring.
"""

import json
import os
import threading
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Human feedback log — one JSON object per line (JSONL)
FEEDBACK_FILE = os.path.join(_BACKEND, "memory", "data", "feedback.jsonl")
# Fine-tuning dataset — prompt/completion pairs with rating >= "up"
DATASET_FILE = os.path.join(_BACKEND, "memory", "data", "finetune_dataset.jsonl")

_lock = threading.Lock()


def _ensure_dirs():
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)


def record_feedback(
    message_id: str,
    user_input: str,
    reply: str,
    rating: str,  # "up" or "down"
    intent: str = "general",
    comment: str = "",
    confidence: float = 0.0,
) -> dict:
    """
    Record user feedback. Returns the saved entry.
    Triggers deep scoring for thumbs-down responses.
    """
    _ensure_dirs()
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "message_id": message_id,
        "input": user_input[:300],
        "reply": reply[:600],
        "rating": rating,
        "intent": intent,
        "comment": comment[:200],
        "confidence": confidence,
    }

    with _lock:
        with open(FEEDBACK_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # Thumbs up → append to fine-tuning dataset
    if rating == "up":
        _append_to_dataset(user_input, reply, intent, session_id=message_id[:8])

    # Thumbs down → trigger immediate deep scoring
    if rating == "down":
        threading.Thread(
            target=_trigger_deep_score,
            args=(user_input, reply, entry["ts"]),
            daemon=True,
        ).start()
        logger.info("👎 Feedback DOWN [%s] — deep score triggered", message_id[:8])
    else:
        logger.info("👍 Feedback UP [%s]", message_id[:8])

    return entry


# Minimum unique sessions that must approve before dataset inclusion
_QUALITY_GATE = int(os.getenv("FEEDBACK_QUALITY_GATE", "3"))

# Pending approvals: input_hash -> set of session_ids that approved
_pending_approvals: dict = {}
_pending_lock = threading.Lock()


def _input_hash(user_input: str, reply: str) -> str:
    import hashlib

    return hashlib.sha256(f"{user_input[:200]}:{reply[:400]}".encode()).hexdigest()[:16]


def _append_to_dataset(
    user_input: str, reply: str, intent: str, session_id: str = "default"
):
    """
    Quality-gated dataset append (E-10 fix).
    Requires _QUALITY_GATE unique sessions to approve before adding to dataset.
    Prevents accidental dataset poisoning from single-user thumbs-up.
    """
    key = _input_hash(user_input, reply)

    with _pending_lock:
        if key not in _pending_approvals:
            _pending_approvals[key] = {
                "sessions": set(),
                "user_input": user_input,
                "reply": reply,
                "intent": intent,
            }
        _pending_approvals[key]["sessions"].add(session_id)
        approved_count = len(_pending_approvals[key]["sessions"])

    if approved_count >= _QUALITY_GATE:
        record = {
            "ts": datetime.utcnow().isoformat(),
            "intent": intent,
            "prompt": user_input[:300],
            "completion": reply[:600],
            "approvals": approved_count,
        }
        with _lock:
            with open(DATASET_FILE, "a") as f:
                f.write(json.dumps(record) + "\n")
        with _pending_lock:
            _pending_approvals.pop(key, None)
        logger.info(
            "✅ Dataset entry approved (%d sessions): %s...",
            approved_count,
            user_input[:40],
        )
    else:
        logger.debug(
            "⏳ Pending dataset entry (%d/%d sessions): %s...",
            approved_count,
            _QUALITY_GATE,
            user_input[:40],
        )


def _trigger_deep_score(user_input: str, reply: str, ts: str):
    """Run LLM deep scoring immediately for thumbs-down responses."""
    try:
        from core.self_improve import _deep_score_async

        _deep_score_async(user_input, reply, ts)
    except Exception as e:
        logger.warning("Deep score failed: %s", e)


def get_stats() -> dict:
    """Return thumbs up/down counts per intent."""
    _ensure_dirs()
    counts: dict = {}
    total_up = total_down = 0

    try:
        with open(FEEDBACK_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    intent = entry.get("intent", "general")
                    rating = entry.get("rating", "")
                    counts.setdefault(intent, {"up": 0, "down": 0})
                    if rating == "up":
                        counts[intent]["up"] += 1
                        total_up += 1
                    elif rating == "down":
                        counts[intent]["down"] += 1
                        total_down += 1
                except Exception:
                    continue
    except FileNotFoundError:
        pass

    total = total_up + total_down
    return {
        "total": total,
        "thumbs_up": total_up,
        "thumbs_down": total_down,
        "approval_rate": round(total_up / total * 100, 1) if total else 0,
        "by_intent": counts,
        "dataset_size": _count_lines(DATASET_FILE),
    }


def get_recent(n: int = 20) -> list:
    """Return the n most recent feedback entries."""
    _ensure_dirs()
    lines = []
    try:
        with open(FEEDBACK_FILE) as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass
    results = []
    for line in reversed(lines[-n:]):
        try:
            results.append(json.loads(line))
        except Exception:
            continue
    return results


def _count_lines(path: str) -> int:
    try:
        with open(path) as f:
            return sum(1 for _ in f)
    except FileNotFoundError:
        return 0
