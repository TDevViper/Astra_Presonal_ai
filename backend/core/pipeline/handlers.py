"""
core/pipeline/handlers.py — All ASTRA pipeline handlers.

Each handler is a single responsibility class.
Order matters — register them in PipelineRegistry in priority order.
"""

from __future__ import annotations
import logging
from typing import Optional
from core.pipeline.base import Handler, RequestContext, Reply

logger = logging.getLogger(__name__)


# ── 1. Mode Switch ────────────────────────────────────────────────────────────


class ModeSwitchHandler(Handler):
    name = "mode_switch"

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        try:
            from personality.modes import detect_mode_switch, set_mode, get_mode_banner

            mode = detect_mode_switch(ctx.user_input)
            if mode:
                set_mode(mode)
                return Reply(
                    text=get_mode_banner(),
                    intent="mode_switch",
                    agent="system",
                    confidence=1.0,
                )
        except Exception as e:
            logger.warning("ModeSwitchHandler: %s", e)
        return None


# ── 2. Cache ──────────────────────────────────────────────────────────────────


class CacheHandler(Handler):
    name = "cache"

    def __init__(self, cache):
        self._cache = cache

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        if ctx.vision_mode:
            return None
        try:
            cached = self._cache.get(ctx.user_input, ctx.session_id)
            if cached:
                return Reply(
                    text=cached.get("reply", ""),
                    intent=cached.get("intent", "general"),
                    agent=cached.get("agent", "cache"),
                    confidence=cached.get("confidence", 0.8),
                )
        except Exception as e:
            logger.warning("CacheHandler: %s", e)
        return None


# ── 3. Chain Planner ──────────────────────────────────────────────────────────


class ChainHandler(Handler):
    name = "chain"

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        try:
            from tools.chain_planner import detect_chain, execute_chain

            chain = detect_chain(ctx.user_input)
            if chain:
                from core.brain_singleton import get_brain

                reply = execute_chain(chain, get_brain())
                if reply:
                    return Reply(
                        text=reply,
                        intent="chain",
                        agent="chain_executor",
                        confidence=0.9,
                    )
        except Exception as e:
            logger.debug("ChainHandler: %s", e)
        return None


# ── 4. Quick Tools ────────────────────────────────────────────────────────────


class QuickToolHandler(Handler):
    name = "quick_tools"

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        try:
            from tools.quick_tools import handle_quick_tool

            result = handle_quick_tool(ctx.user_input)
            if result:
                reply_text, intent, agent = result
                return Reply(
                    text=reply_text,
                    intent=intent,
                    agent=agent,
                    confidence=1.0,
                    tool_used=True,
                )
        except Exception as e:
            logger.debug("QuickToolHandler: %s", e)
        return None


# ── 5. Intent Shortcut ────────────────────────────────────────────────────────


class IntentShortcutHandler(Handler):
    name = "intent_shortcut"

    def __init__(self, cache):
        self._cache = cache

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        if ctx.vision_mode:
            return None
        try:
            from intents.shortcuts import detect_intent

            shortcut = detect_intent(ctx.user_input, ctx.user_name)
            if shortcut:
                from core.confidence import score as conf_score

                r = Reply(
                    text=shortcut,
                    intent="shortcut",
                    agent="intent_handler",
                    confidence=conf_score("shortcut", "shortcut"),
                )
                self._cache.set(
                    ctx.user_input, r.to_dict(ctx.emotion_label), ctx.session_id
                )
                return r
        except Exception as e:
            logger.debug("IntentShortcutHandler: %s", e)
        return None


# ── 6. Self Query ─────────────────────────────────────────────────────────────


class SelfQueryHandler(Handler):
    name = "self_query"

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        try:
            from core.self_awareness import is_self_query, get_self_response

            if is_self_query(ctx.user_input):
                reply = get_self_response(ctx.user_input, ctx.user_name)
                return Reply(
                    text=reply, intent="self_awareness", agent="self", confidence=1.0
                )
        except Exception as e:
            logger.debug("SelfQueryHandler: %s", e)
        return None


# ── 7. Tool Dispatch ──────────────────────────────────────────────────────────


class ToolDispatchHandler(Handler):
    name = "tool_dispatch"

    def __init__(self, tool_executor, capabilities):
        self._tools = tool_executor
        self._caps = capabilities

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        try:
            from tools.tool_router import detect_tool, detect_compound

            compound = detect_compound(ctx.user_input)
            if compound:
                return Reply(
                    text=compound,
                    intent="shortcut",
                    agent="system_controller",
                    confidence=1.0,
                    tool_used=True,
                )
            tool = detect_tool(ctx.user_input)
            if tool and self._caps.is_enabled(tool):
                result = self._tools.execute(
                    tool, ctx.user_input, ctx.memory, ctx.user_name
                )
                if result:
                    return Reply(
                        text=result.get("reply", ""),
                        intent=result.get("intent", "tool"),
                        agent=result.get("agent", tool),
                        confidence=result.get("confidence", 0.9),
                        tool_used=True,
                    )
        except Exception as e:
            logger.debug("ToolDispatchHandler: %s", e)
        return None


# ── 8. Memory ─────────────────────────────────────────────────────────────────


class MemoryHandler(Handler):
    name = "memory"

    def __init__(self, mem_manager):
        self._mem = mem_manager

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        try:
            from intents.classifier import is_question_like
            from core.confidence import score as conf_score

            # Fact extraction
            fact, memory = self._mem.extract_and_store_fact(
                ctx.user_input, ctx.memory, ctx.user_name
            )
            if fact:
                ctx.memory.update(memory)
                self._mem.save(ctx.memory)
                if not is_question_like(ctx.user_input):
                    return Reply(
                        text=self._mem.acknowledge_fact(fact),
                        intent="memory_storage",
                        agent="memory",
                        confidence=conf_score("memory_storage", "memory_storage"),
                        memory_updated=True,
                    )

            # Memory recall
            recalled = self._mem.recall(ctx.user_input, ctx.memory, ctx.user_name)
            if recalled:
                self._mem.save(ctx.memory)
                return Reply(
                    text=recalled,
                    intent="memory_recall",
                    agent="memory",
                    confidence=conf_score("memory_recall", "memory_recall"),
                )
        except Exception as e:
            logger.debug("MemoryHandler: %s", e)
        return None


# ── 9. Web Search ─────────────────────────────────────────────────────────────


class WebSearchHandler(Handler):
    name = "web_search"

    def __init__(self, search_agent, capabilities, model_manager):
        self._search = search_agent
        self._caps = capabilities
        self._mm = model_manager

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        import re as _re

        _SEARCH_PATTERN = _re.compile(
            r"\b(search for|google|look up|find out|latest|current (price|status|version)|"
            r"news today|what.s happening|who is (the )?ceo|who (won|leads|runs)|"
            r"weather (in|today|tomorrow)|price of|stock price|breaking news)\b",
            _re.IGNORECASE,
        )
        _LOCAL = {"my project", "my code", "in the project", "my file", "my folder"}

        if not self._caps.is_enabled("web_search"):
            return None
        if not _SEARCH_PATTERN.search(ctx.user_input):
            return None
        if any(w in ctx.user_input.lower() for w in _LOCAL):
            return None

        try:
            from core.confidence import score as conf_score

            self._search.model = self._mm.select_model(ctx.user_input, "research")
            query = ctx.user_input
            for trigger in ["search for ", "search ", "google ", "look up ", "find "]:
                if query.lower().startswith(trigger):
                    query = query[len(trigger) :].strip()
                    break
            result = self._search.run(query, ctx.user_name)
            return Reply(
                text=result["reply"],
                intent="web_search",
                agent="web_search_agent",
                confidence=conf_score("web_search_agent", "web_search"),
                tool_used=True,
                citations=result.get("citations") or [],
                results_count=result.get("results_count", 0),
            )
        except Exception as e:
            logger.warning("WebSearchHandler: %s", e)
        return None


# ── 10. LLM ───────────────────────────────────────────────────────────────────


class LLMHandler(Handler):
    """
    Terminal handler — always produces a reply.
    If streaming=True, returns a sentinel Reply with stream_sentinel=True
    so the caller can handle streaming directly.
    """

    name = "llm"

    def __init__(self, llm_engine, ctx_builder, model_manager):
        self._llm = llm_engine
        self._ctx = ctx_builder
        self._mm = model_manager

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        from core.confidence import score as conf_score

        try:
            query_intent = ctx.query_intent or self._mm.classify_query_intent(
                ctx.user_input
            )
            selected_model = ctx.selected_model or self._mm.select_model(
                ctx.user_input, query_intent
            )

            system_prompt, sem_conf = self._ctx.build(
                ctx.user_input,
                ctx.user_name,
                ctx.memory,
                ctx.emotion_label,
                query_intent,
                ctx.history,
            )

            # Inject RAG context
            try:
                from rag.rag_engine import query_rag, should_use_rag

                if should_use_rag(ctx.user_input):
                    rag_ctx = query_rag(ctx.user_input, top_k=3)
                    if rag_ctx:
                        system_prompt += f"\n\nRELEVANT KNOWLEDGE:\n{rag_ctx}"
            except Exception as _e:
                logger.debug("RAG: %s", _e)

            if ctx.streaming:
                # Return sentinel — caller streams directly
                return Reply(
                    text="",
                    intent=query_intent,
                    agent=f"ollama/{selected_model}",
                    confidence=max(
                        conf_score(f"ollama/{selected_model}", query_intent), sem_conf
                    ),
                    stream_sentinel=True,
                    extra={
                        "system_prompt": system_prompt,
                        "selected_model": selected_model,
                        "query_intent": query_intent,
                    },
                )

            # Blocking LLM call
            reply = self._llm.try_react(
                ctx.user_input, selected_model, system_prompt, ctx.user_name
            )
            if not reply:
                reply = self._llm.call(
                    ctx.user_input,
                    system_prompt,
                    selected_model,
                    query_intent,
                    ctx.history,
                )

            final_conf = max(
                conf_score(f"ollama/{selected_model}", query_intent), sem_conf
            )
            return Reply(
                text=reply,
                intent=query_intent,
                agent=f"ollama/{selected_model}",
                confidence=final_conf,
            )

        except Exception as e:
            logger.error("LLMHandler: %s", e, exc_info=True)
            return Reply(
                text="Something went wrong.",
                intent="error",
                agent="error_handler",
                confidence=0.0,
            )
