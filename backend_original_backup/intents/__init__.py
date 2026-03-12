# backend/astra_engine/intents/__init__.py
from .shortcuts import detect_intent
from .classifier import is_question_like

__all__ = ["detect_intent", "is_question_like"]
