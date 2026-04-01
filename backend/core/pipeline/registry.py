"""
core/pipeline/registry.py — Ordered handler chain.

Handlers are tried in registration order.
First non-None reply wins and terminates the chain.
"""

from __future__ import annotations
import logging
from typing import List, Optional
from core.pipeline.base import Handler, RequestContext, Reply

logger = logging.getLogger(__name__)


class PipelineRegistry:
    def __init__(self):
        self._handlers: List[Handler] = []

    def register(self, handler: Handler) -> "PipelineRegistry":
        self._handlers.append(handler)
        logger.debug("Pipeline: registered %s", handler)
        return self

    def run(self, ctx: RequestContext) -> Optional[Reply]:
        for handler in self._handlers:
            try:
                result = handler.handle(ctx)
                if result is not None:
                    logger.debug("Pipeline: %s handled request", handler)
                    return result
            except Exception as e:
                logger.error(
                    "Pipeline handler %s failed: %s", handler, e, exc_info=True
                )
                # Continue to next handler on error — never crash the pipeline
        return None

    def __repr__(self):
        names = [h.name for h in self._handlers]
        return f"<PipelineRegistry [{' → '.join(names)}]>"
