# ==========================================
# core/post_processor.py
# ==========================================
import logging
from typing import Dict

from agents.critic import critic_review
from reflection.refinement import refine_reply
from core.truth_guard import TruthGuard
from utils.polisher import polish_reply
from utils.limiter import limit_words, detect_intent_for_limit
from emotion.emotion_responder import choose_reply as emotion_reply
from core.proactive import get_proactive_suggestion

logger = logging.getLogger(__name__)

class PostProcessor:
    def __init__(self, truth_guard: TruthGuard):
        self._tg = truth_guard

    def process(self, reply, user_input, user_name, memory, selected_model, query_intent, emotion_label, emotion_score) -> str:
        reply = self._critic(reply, user_name, memory, user_input, selected_model, query_intent)
        reply = self._refine(reply, memory, user_name)
        reply = self._truth_guard(reply)
        reply = self._polish(reply)
        reply = self._limit(reply, user_input)
        reply = self._emotion_prefix(reply, emotion_label, emotion_score, user_name, memory)
        reply = self._proactive(reply, user_input, memory, user_name)
        return reply

    def _critic(self, reply, user_name, memory, user_input, model, intent):
        try:
            return critic_review(reply, user_name, memory, user_input=user_input, model=model, intent=intent)
        except Exception as e:
            logger.warning("critic_review failed: %s", e)
            return reply

    def _refine(self, reply, memory, user_name):
        try:
            return refine_reply(reply, memory, user_name)
        except Exception as e:
            logger.warning("refine_reply failed: %s", e)
            return reply

    def _truth_guard(self, reply):
        try:
            is_valid, violation = self._tg.validate(reply)
            if not is_valid:
                logger.warning("TruthGuard violation: %s", violation)
                return self._tg.get_safe_reply(violation)
        except Exception as e:
            logger.warning("truth_guard failed: %s", e)
        return reply

    def _polish(self, reply):
        try:
            return polish_reply(reply)
        except Exception as e:
            logger.warning("polish_reply failed: %s", e)
            return reply

    def _limit(self, reply, user_input):
        try:
            return limit_words(reply, intent=detect_intent_for_limit(user_input))
        except Exception as e:
            logger.warning("limit_words failed: %s", e)
            return reply

    def _emotion_prefix(self, reply, emotion_label, emotion_score, user_name, memory):
        if emotion_score > 0.7 and emotion_label in {"sad", "angry", "anxious", "tired"}:
            try:
                return f"{emotion_reply(emotion_label, emotion_score, user_name, memory)} {reply}"
            except Exception as e:
                logger.warning("emotion_reply failed: %s", e)
        return reply

    def _proactive(self, reply, user_input, memory, user_name):
        try:
            suggestion = get_proactive_suggestion(user_input, memory, user_name)
            if suggestion:
                return reply + "\n\n" + suggestion
        except Exception as e:
            logger.warning("proactive_suggestion failed: %s", e)
        return reply
