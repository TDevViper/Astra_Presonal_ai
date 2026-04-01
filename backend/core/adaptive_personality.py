# core/adaptive_personality.py
# Learns user's communication preferences from response logs
# Auto-tunes system prompt weekly based on quality scores
import json
import os
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE_FILE = os.path.join(_BACKEND_DIR, "memory", "data", "user_style.json")
LAST_RUN_KEY = "last_refine_ts"


def _load_style() -> Dict:
    try:
        if os.path.exists(STYLE_FILE):
            with open(STYLE_FILE) as f:
                return json.load(f)
    except Exception as _e:
        logger.debug("adaptive_personality: %s", _e)
    return {
        "response_length": "medium",  # short | medium | verbose
        "format_preference": "prose",  # prose | bullets | mixed
        "tone": "direct",  # friendly | direct | technical
        "code_style": "explained",  # raw | explained
        "overrides": [],  # list of prompt lines to inject
        LAST_RUN_KEY: 0,
    }


def _save_style(style: Dict):
    os.makedirs(os.path.dirname(STYLE_FILE), exist_ok=True)
    with open(STYLE_FILE, "w") as f:
        json.dump(style, f, indent=2)


def get_style_addon() -> str:
    """
    Returns a short system prompt addon based on learned user style.
    Injected into every system prompt.
    """
    style = _load_style()
    parts = []

    length = style.get("response_length", "medium")
    if length == "short":
        parts.append("Keep responses under 3 sentences unless asked for more detail.")
    elif length == "verbose":
        parts.append("Provide thorough, detailed responses with examples.")

    fmt = style.get("format_preference", "prose")
    if fmt == "bullets":
        parts.append("Use bullet points for lists and multi-part answers.")
    elif fmt == "prose":
        parts.append("Write in natural prose, avoid unnecessary bullet points.")

    tone = style.get("tone", "direct")
    if tone == "friendly":
        parts.append("Use a warm, conversational tone.")
    elif tone == "technical":
        parts.append("Use precise technical language.")
    elif tone == "direct":
        parts.append("Be direct and concise.")

    if style.get("overrides"):
        parts.extend(style["overrides"][-3:])

    return " ".join(parts)


def maybe_refine(force: bool = False) -> Optional[str]:
    """
    Run weekly auto-refinement using self_improve data.
    Returns the new style addon string if refined, None if skipped.
    """
    style = _load_style()
    now = time.time()
    week = 7 * 24 * 3600

    if not force and (now - style.get(LAST_RUN_KEY, 0)) < week:
        return None

    logger.info("🧠 Running adaptive personality refinement...")
    try:
        from core.self_improve import (
            analyze_weak_spots,
            auto_refine_prompts,
            _load_logs,
        )

        logs = _load_logs()
        if len(logs) < 20:
            logger.info("Not enough data yet (%d logs)", len(logs))
            return None

        # Detect response length preference from ratings
        high_rated = [
            ln for ln in logs if (ln.get("rating") or ln.get("h_score", 0)) >= 0.7
        ]
        if high_rated:
            avg_words = sum(
                len(ln.get("response", "").split()) for ln in high_rated
            ) / len(high_rated)
            if avg_words < 40:
                style["response_length"] = "short"
            elif avg_words > 150:
                style["response_length"] = "verbose"
            else:
                style["response_length"] = "medium"

        # Detect format preference
        bullet_count = sum(
            1
            for ln in high_rated
            if "•" in ln.get("response", "") or "- " in ln.get("response", "")
        )
        if bullet_count > len(high_rated) * 0.6:
            style["format_preference"] = "bullets"
        else:
            style["format_preference"] = "prose"

        # Get LLM-generated prompt fixes
        fixes = auto_refine_prompts()
        if fixes and "performing well" not in fixes and "Error" not in fixes:
            # Extract each numbered point as an override
            import re

            points = re.findall(r"\d+\.\s+(.+?)(?=\d+\.|$)", fixes, re.DOTALL)
            style["overrides"] = [
                p.strip()[:80] for p in points[:3] if len(p.strip()) > 10
            ]
            logger.info("✅ Style overrides updated: %d rules", len(style["overrides"]))

        style[LAST_RUN_KEY] = now
        _save_style(style)
        return get_style_addon()

    except Exception as e:
        logger.warning("adaptive_personality refine failed: %s", e)
        return None


def update_style_manually(key: str, value: str) -> bool:
    """Allow user to directly set style preferences via chat."""
    valid = {
        "response_length": ["short", "medium", "verbose"],
        "format_preference": ["prose", "bullets", "mixed"],
        "tone": ["friendly", "direct", "technical"],
        "code_style": ["raw", "explained"],
    }
    if key not in valid or value not in valid[key]:
        return False
    style = _load_style()
    style[key] = value
    _save_style(style)
    logger.info("Style updated: %s = %s", key, value)
    return True
