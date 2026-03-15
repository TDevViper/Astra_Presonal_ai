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

            # Inject long-term conversation summaries
            summary_ctx = ""
            try:
                from memory.summarizer import get_recent_context
                summary_ctx = get_recent_context(memory, max_summaries=3)
            except Exception:
                pass

            system_prompt = build_system_prompt(
                user_name=user_name,
                memory=memory,
                emotion=emotion_label,
                intent=query_intent,
                semantic_ctx=semantic_ctx,
                episodic_ctx=episodic_ctx,
                addon=addon,
            )

            if summary_ctx:
                system_prompt = summary_ctx + "\n\n" + system_prompt

            # Inject visual memory context for vision-related queries
            vision_keywords = ["screen", "see", "show", "camera", "error", "what's on"]
            if any(w in user_input.lower() for w in vision_keywords):
                try:
                    from core.visual_memory import build_visual_context
                    visual_ctx = build_visual_context(user_input)
                    if visual_ctx:
                        system_prompt += visual_ctx
                except Exception:
                    pass

            # Inject adaptive personality style
            try:
                from core.adaptive_personality import get_style_addon
                style_addon = get_style_addon()
                if style_addon:
                    system_prompt += f"\n\nSTYLE: {style_addon}"
            except Exception:
                pass

            # Inject live ambient context
            try:
                from core.ambient import get_context_string
                ambient_ctx = get_context_string()
                if ambient_ctx:
                    system_prompt += f"\n\nCURRENT ENVIRONMENT: {ambient_ctx}"
            except Exception:
                pass

            return system_prompt, sem_conf

        except Exception as e:
            logger.warning("ContextBuilder.build failed: %s", e)
            fallback = (
                f"You are ASTRA, a smart personal AI assistant for {user_name}. "
                "Be concise, accurate, and direct."
            )
            return fallback, sem_conf
