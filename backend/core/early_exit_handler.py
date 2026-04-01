# core/early_exit_handler.py
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_briefing_shown = False  # show once per session only


class EarlyExitHandler:
    def check_mode_switch(self, user_input: str) -> Optional[str]:
        try:
            from personality.modes import detect_mode_switch, set_mode, get_mode_banner

            mode = detect_mode_switch(user_input)
            if mode:
                set_mode(mode)
                return get_mode_banner()
        except Exception as e:
            logger.warning("check_mode_switch failed: %s", e)
        return None

    def check_chain(self, user_input: str, brain) -> Optional[str]:
        try:
            from tools.chain_planner import detect_chain, execute_chain

            chain = detect_chain(user_input)
            if chain:
                return execute_chain(chain, brain)
        except Exception as e:
            logger.debug("check_chain failed: %s", e)
        return None

    def check_briefing(self, memory: dict):
        return None  # disabled

    def check_quick_tools(self, user_input: str) -> Optional[Tuple[str, str, str]]:
        try:
            from tools.quick_tools import handle_quick_tool

            return handle_quick_tool(user_input)
        except Exception as e:
            logger.debug("check_quick_tools failed: %s", e)
        return None

    def check_intent_shortcut(self, user_input: str, user_name: str) -> Optional[str]:
        try:
            from intents.shortcuts import detect_intent

            return detect_intent(user_input, user_name)
        except Exception as e:
            logger.debug("check_intent_shortcut failed: %s", e)
        return None

    def check_self_query(self, user_input: str, user_name: str) -> Optional[str]:
        try:
            from core.self_awareness import is_self_query, get_self_response

            if is_self_query(user_input):
                return get_self_response(user_input, user_name)
        except Exception as e:
            logger.debug("check_self_query failed: %s", e)
        return None
