# core/context_builder.py
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ContextBuilder:

    def build(self, user_input: str, user_name: str, memory: Dict,
              emotion_label: str, query_intent: str,
              conversation_history: List[Dict]) -> Tuple[str, float]:
        """Returns (system_prompt, semantic_confidence)."""
        sem_conf = 0.0
        try:
            from personality.system import build_system_prompt
            from memory.semantic_recall import build_semantic_context
            from memory.episodic import build_episodic_context
            from personality.modes import get_system_addon

            semantic_ctx, sem_conf = build_semantic_context(user_input, user_name)
            episodic_ctx           = build_episodic_context(user_input, user_name)
            addon                  = get_system_addon()

            system_prompt = build_system_prompt(
                user_name=user_name,
                memory=memory,
                emotion=emotion_label,
                query_intent=query_intent,
                semantic_ctx=semantic_ctx,
                episodic_ctx=episodic_ctx,
                addon=addon,
            )
            return system_prompt, sem_conf

        except Exception as e:
            logger.warning("ContextBuilder.build failed: %s", e)
            fallback = (
                f"You are ASTRA, a smart personal AI assistant for {user_name}. "
                "Be concise, accurate, and direct."
            )
            return fallback, sem_conf
