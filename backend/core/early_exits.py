# core/early_exits.py
# Shared early-exit logic used by both Brain.process() and Brain.process_stream()
import logging
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)


def handle_early_exits(
    user_input: str,
    vision_mode: bool,
    exit_handler,
    cache,
    mem_manager,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Runs all early-exit checks shared between process() and process_stream().
    Returns (reply, intent) if an early exit is found, else (None, None).
    """
    # 1. Mode switch
    mode_reply = exit_handler.check_mode_switch(user_input)
    if mode_reply:
        return mode_reply, "mode_switch"

    # 2. Cache
    if not vision_mode:
        cached = cache.get(user_input)
        if cached:
            return cached.get("reply", ""), "cache"

    # 3. Chain planner
    chain_reply = exit_handler.check_chain(user_input, None)
    if chain_reply:
        return chain_reply, "chain"

    return None, None


def handle_user_exits(
    user_input: str,
    user_name: str,
    vision_mode: bool,
    exit_handler,
    mem_manager,
    memory: Dict,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Runs user-context exits (requires memory to be loaded).
    Returns (reply, intent) if found, else (None, None).
    """
    # Briefing
    brief = exit_handler.check_briefing(memory)
    if brief:
        return brief, "briefing"

    # Quick tools
    qt = exit_handler.check_quick_tools(user_input)
    if qt:
        reply, intent, agent = qt
        return reply, intent

    # Intent shortcut
    shortcut = exit_handler.check_intent_shortcut(user_input, user_name)
    if shortcut and not vision_mode:
        return shortcut, "shortcut"

    # Self query
    self_reply = exit_handler.check_self_query(user_input, user_name)
    if self_reply:
        return self_reply, "self_awareness"

    return None, None
