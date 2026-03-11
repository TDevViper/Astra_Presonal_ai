# ==========================================
# core/context_builder.py
# ==========================================
import logging
from typing import Dict, List, Tuple

from memory.semantic_recall import build_semantic_context
from memory.episodic import build_episodic_context
from personality.system import build_system_prompt
from personality.modes import get_system_addon
from utils.language_detector import detect_language, get_language_instruction

logger = logging.getLogger(__name__)

class ContextBuilder:
    def build(self, user_input, user_name, memory, emotion_label, query_intent, conversation_history) -> Tuple[str, float]:
        semantic_ctx, sem_conf = self._semantic(user_input, user_name)
        semantic_ctx           = self._enrich_rag(user_input, semantic_ctx)
        tool_ctx               = self._parallel_tools(user_input)
        if tool_ctx:
            semantic_ctx = (semantic_ctx + "\n\nLIVE CONTEXT:\n" + tool_ctx) if semantic_ctx else "LIVE CONTEXT:\n" + tool_ctx
        episodic_ctx = self._episodic(user_input, user_name)
        lang_instr   = get_language_instruction(detect_language(user_input))
        prompt = build_system_prompt(
            user_name=user_name, memory=memory, emotion=emotion_label,
            intent=query_intent, episodic_ctx=episodic_ctx, semantic_ctx=semantic_ctx,
            lang_instruction=lang_instr, conversation_history=conversation_history,
        ) + get_system_addon()
        logger.info("context_builder | sem=%d tool=%d", len(semantic_ctx), len(tool_ctx))
        return prompt, sem_conf

    def _semantic(self, user_input, user_name):
        try:
            return build_semantic_context(user_input, user_name=user_name)
        except Exception as e:
            logger.warning("semantic_context failed: %s", e)
            return "", 0.0

    def _enrich_rag(self, user_input, semantic_ctx):
        try:
            from rag.rag_engine import query_rag, should_use_rag
            if should_use_rag(user_input):
                rag = query_rag(user_input, top_k=3)
                if rag:
                    return (semantic_ctx + "\n\nFROM YOUR FILES:\n" + rag) if semantic_ctx else "FROM YOUR FILES:\n" + rag
        except Exception as e:
            logger.warning("rag_engine failed: %s", e)
        return semantic_ctx

    def _parallel_tools(self, user_input):
        try:
            from core.orchestrator import run_parallel_tools
            results = run_parallel_tools(user_input)
            if results:
                return "\n".join(f"[{t.upper()}]: {r}" for t, r in results.items() if r and "error" not in str(r).lower()[:20])
        except Exception as e:
            logger.warning("parallel_tools failed: %s", e)
        return ""

    def _episodic(self, user_input, user_name):
        try:
            return build_episodic_context(user_input, user_name)
        except Exception as e:
            logger.warning("episodic_context failed: %s", e)
            return ""
