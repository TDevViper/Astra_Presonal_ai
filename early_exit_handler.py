# ==========================================
# core/early_exit_handler.py
# ==========================================
import logging
from typing import Dict, Optional, Tuple

from intents.shortcuts import detect_intent
from core.self_awareness import is_self_query, get_self_response
from core.proactive import get_session_summary
from personality.modes import detect_mode_switch, set_mode, get_mode_banner
from tools.system_controller import handle_system_command
from tools.calendar_tool import handle_calendar_command
from tools.whatsapp_tool import handle_whatsapp_command
from tools.web_search import handle_search_command

logger = logging.getLogger(__name__)

_BYE_WORDS = {"bye", "goodbye", "exit", "quit", "see you", "good night", "cya"}
_QUICK_HANDLERS = [
    (handle_search_command,   "web_search",     "web_search_agent"),
    (handle_whatsapp_command, "whatsapp",       "whatsapp"),
    (handle_calendar_command, "calendar",       "calendar"),
    (handle_system_command,   "system_control", "system_controller"),
]

class EarlyExitHandler:
    def check_mode_switch(self, user_input: str) -> Optional[str]:
        mode = detect_mode_switch(user_input)
        if mode:
            set_mode(mode)
            logger.info("Mode switch → %s", mode)
            return f"Mode switched: {get_mode_banner()}"
        return None

    def check_chain(self, user_input: str, brain) -> Optional[str]:
        try:
            from tools.chain_planner import detect_chain, build_chain_plan, execute_chain
            steps = detect_chain(user_input)
            if steps:
                result = execute_chain(build_chain_plan(user_input, steps), brain)
                logger.info("Chain executed: %d steps", len(steps))
                return result
        except Exception as e:
            logger.warning("chain_planner failed: %s", e)
        return None

    def check_briefing(self, memory: Dict) -> Optional[str]:
        try:
            from briefing import should_give_briefing, generate_morning_brief, mark_briefing_done
            from memory.memory_engine import save_memory
            if should_give_briefing(memory):
                brief  = generate_morning_brief(memory)
                memory = mark_briefing_done(memory)
                save_memory(memory)
                logger.info("Morning briefing delivered")
                return brief
        except Exception as e:
            logger.warning("briefing check failed: %s", e)
        return None

    def check_quick_tools(self, user_input: str) -> Optional[Tuple[str, str, str]]:
        for handler, intent, agent in _QUICK_HANDLERS:
            try:
                result = handler(user_input)
                if result:
                    logger.info("Quick tool hit: %s", agent)
                    return result, intent, agent
            except Exception as e:
                logger.warning("%s handler failed: %s", agent, e)
        return None

    def check_intent_shortcut(self, user_input: str, user_name: str) -> Optional[str]:
        try:
            shortcut = detect_intent(user_input, user_name)
            if shortcut:
                if any(w in user_input.lower() for w in _BYE_WORDS):
                    try:
                        summary = get_session_summary(user_name)
                        if summary:
                            shortcut += "\n\n📊 " + summary
                    except Exception as e:
                        logger.warning("session_summary failed: %s", e)
                return shortcut
        except Exception as e:
            logger.warning("detect_intent failed: %s", e)
        return None

    def check_self_query(self, user_input: str, user_name: str) -> Optional[str]:
        try:
            if is_self_query(user_input):
                logger.info("Self-query detected")
                return get_self_response(user_input, user_name)
        except Exception as e:
            logger.warning("self_query check failed: %s", e)
        return None
