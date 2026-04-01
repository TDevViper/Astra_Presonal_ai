"""
core/pipeline/builder.py — Constructs the default ASTRA pipeline.

Import build_pipeline() once at Brain init time.
"""

from core.pipeline.registry import PipelineRegistry
from core.pipeline.handlers import (
    ModeSwitchHandler,
    CacheHandler,
    ChainHandler,
    QuickToolHandler,
    IntentShortcutHandler,
    SelfQueryHandler,
    ToolDispatchHandler,
    MemoryHandler,
    WebSearchHandler,
    LLMHandler,
)


def build_pipeline(brain) -> PipelineRegistry:
    """Build the default handler chain from a Brain instance."""
    registry = PipelineRegistry()
    registry.register(ModeSwitchHandler())
    registry.register(CacheHandler(brain._cache))
    registry.register(ChainHandler())
    registry.register(QuickToolHandler())
    registry.register(IntentShortcutHandler(brain._cache))
    registry.register(SelfQueryHandler())
    registry.register(ToolDispatchHandler(brain._tools, brain.capabilities))
    registry.register(MemoryHandler(brain._mem))
    registry.register(
        WebSearchHandler(brain.search_agent, brain.capabilities, brain.model_manager)
    )
    registry.register(LLMHandler(brain._llm, brain._ctx, brain.model_manager))
    return registry
