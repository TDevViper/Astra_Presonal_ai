"""
core/pipeline/base.py — Pipeline primitives for ASTRA.

Each pipeline stage is a Handler subclass implementing handle().
Handlers are composed into a chain — first non-None reply wins.
Adding a new capability = adding a new Handler, never editing brain.py.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """
    Immutable per-request context passed through the pipeline.
    No shared mutable state — everything a handler needs is here.
    """

    user_input: str
    session_id: str = "default"
    vision_mode: bool = False
    streaming: bool = False
    history: List[Dict] = field(default_factory=list)
    memory: Dict = field(default_factory=dict)
    user_name: str = "User"
    emotion_label: str = "neutral"
    emotion_score: float = 0.0
    query_intent: str = ""
    selected_model: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reply:
    """Structured reply from a pipeline handler."""

    text: str
    intent: str = "general"
    agent: str = "unknown"
    confidence: float = 0.6
    tool_used: bool = False
    memory_updated: bool = False
    citations: List = field(default_factory=list)
    results_count: int = 0
    stream_sentinel: bool = False  # True = LLM path, caller should stream

    def to_dict(self, emotion: str = "neutral", confidence_label_fn=None) -> Dict:
        from core.confidence import label as _label

        conf_info = _label(self.confidence)
        d = {
            "reply": self.text,
            "emotion": emotion,
            "intent": self.intent,
            "agent": self.agent,
            "tool_used": self.tool_used,
            "memory_updated": self.memory_updated,
            "confidence": self.confidence,
            "confidence_label": conf_info["text"],
            "confidence_emoji": conf_info["emoji"],
        }
        if self.citations:
            d["citations"] = self.citations
            d["results_count"] = self.results_count
        return d


class Handler:
    """
    Base class for all pipeline handlers.

    Subclasses implement handle() and return a Reply or None.
    Returning None passes control to the next handler in the chain.
    """

    name: str = "base"

    def handle(self, ctx: RequestContext) -> Optional[Reply]:
        raise NotImplementedError

    def __repr__(self):
        return f"<Handler:{self.name}>"
