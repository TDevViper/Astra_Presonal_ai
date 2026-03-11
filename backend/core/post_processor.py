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
        for step in [
            lambda r: self._critic(r, user_name, memory, user_input, selected_model, query_intent),
            lambda r: self._refine(r, memory, user_name),
            lambda r: self._truth_guard(r),
            lambda r: self._polish(r),
            lambda r: self._limit(r, user_input),
            lambda r: self._emotion_prefix(r, emotion_label, emotion_score, user_name, memory),
            lambda r: self._proactive(r, user_input, memory, user_name),
        ]:
            try: reply = step(reply)
            except Exception as e: logger.warning("post_processor step failed: %s", e)
        return reply
    def _critic(self, r, un, m, ui, model, intent):
        try: return critic_review(r, un, m, user_input=ui, model=model, intent=intent)
        except Exception as e: logger.warning("critic_review failed: %s", e); return r
    def _refine(self, r, m, un):
        try: return refine_reply(r, m, un)
        except Exception as e: logger.warning("refine_reply failed: %s", e); return r
    def _truth_guard(self, r):
        try:
            ok, v = self._tg.validate(r)
            if not ok: logger.warning("TruthGuard violation: %s", v); return self._tg.get_safe_reply(v)
        except Exception as e: logger.warning("truth_guard failed: %s", e)
        return r
    def _polish(self, r):
        try: return polish_reply(r)
        except Exception as e: logger.warning("polish_reply failed: %s", e); return r
    def _limit(self, r, ui):
        try: return limit_words(r, intent=detect_intent_for_limit(ui))
        except Exception as e: logger.warning("limit_words failed: %s", e); return r
    def _emotion_prefix(self, r, label, score, un, m):
        if score > 0.7 and label in {"sad","angry","anxious","tired"}:
            try: return f"{emotion_reply(label, score, un, m)} {r}"
            except Exception as e: logger.warning("emotion_reply failed: %s", e)
        return r
    def _proactive(self, r, ui, m, un):
        try:
            s = get_proactive_suggestion(ui, m, un)
            if s: return r + "\n\n" + s
        except Exception as e: logger.warning("proactive_suggestion failed: %s", e)
        return r
