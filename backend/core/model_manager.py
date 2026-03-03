# ==========================================
# core/model_manager.py — Smart Fallback
# GPU server → local fallback automatic
# ==========================================

import logging
import os
import requests
import ollama
from typing import Dict, List

logger = logging.getLogger(__name__)

# Server priority order
OLLAMA_SERVERS = [
    {"name": "RTX 3060 (GPU)",  "url": "http://100.113.54.3:11434"},
    {"name": "Local (Mac CPU)", "url": "http://localhost:11434"},
]

MODEL_PROFILES = {
    "phi3:mini":      {"best_for": ["casual", "memory", "greeting", "simple_question"], "speed": "fast"},
    "llama3.2:3b":    {"best_for": ["reasoning", "analysis", "step_by_step"],           "speed": "fast"},
    "mistral:latest": {"best_for": ["technical", "coding", "research", "detailed"],     "speed": "slow"},
}

INTENT_MODEL_MAP = {
    "casual":          "phi3:mini",
    "memory":          "phi3:mini",
    "greeting":        "phi3:mini",
    "simple_question": "phi3:mini",
    "reasoning":       "llama3.2:3b",
    "step_by_step":    "llama3.2:3b",
    "analysis":        "llama3.2:3b",
    "technical":       "mistral:latest",
    "coding":          "mistral:latest",
    "research":        "mistral:latest",
    "web_search":      "mistral:latest",
}


def _check_server(url: str, timeout: int = 1) -> bool:
    """Ping Ollama server — returns True if alive."""
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def _get_active_server() -> Dict:
    """
    Try servers in priority order.
    Returns first one that responds.
    """
    for server in OLLAMA_SERVERS:
        if _check_server(server["url"]):
            logger.info(f"✅ Using server: {server['name']} ({server['url']})")
            return server
    # Last resort — return local even if not responding
    logger.warning("⚠️  No server responded — defaulting to localhost")
    return OLLAMA_SERVERS[-1]


class ModelManager:

    def __init__(self, default_model: str = "phi3:mini"):
        self.default_model  = default_model
        self.current_model  = default_model
        self._active_server = None
        self._refresh_server()

    def _refresh_server(self):
        """Detect best available server."""
        self._active_server = _get_active_server()
        # Set OLLAMA_HOST env so ollama client uses correct server
        os.environ["OLLAMA_HOST"] = self._active_server["url"]
        self.available_models = self._get_available_models()
        logger.info(f"🖥️  Active: {self._active_server['name']} | Models: {self.available_models}")

    def _get_available_models(self) -> List[str]:
        try:
            import os
            import ollama as _ol
            client = _ol.Client(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
            result = client.list()
            models = []
            for m in result.get("models", []):
                name = m.get("model", m.get("name", ""))
                for known in MODEL_PROFILES:
                    if known in name:
                        models.append(known)
            return models or [self.default_model]
        except Exception as e:
            logger.warning(f"Could not fetch models: {e}")
            return [self.default_model]

    def select_model(self, query: str, intent: str = "casual") -> str:
        # Re-check server on every call — auto-failover
        current_url = os.environ.get("OLLAMA_HOST", "")
        if not _check_server(current_url, timeout=1):
            logger.warning("⚡ Server switched — refreshing...")
            self._refresh_server()

        preferred = INTENT_MODEL_MAP.get(intent, self.default_model)
        if preferred in self.available_models:
            self.current_model = preferred
            return preferred

        # Fallback chain
        for model in ["phi3:mini", "llama3.2:3b", "mistral:latest"]:
            if model in self.available_models:
                logger.warning(f"⚠️  Fallback: {model}")
                self.current_model = model
                return model

        return self.default_model

    def classify_query_intent(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["code", "debug", "function", "algorithm", "implement", "syntax", "error", "bug", "class"]):
            return "coding"
        if any(w in q for w in ["explain", "how does", "what is", "difference between", "compare", "architecture"]):
            return "technical"
        if any(w in q for w in ["search", "find", "latest", "news", "current", "today", "recent"]):
            return "research"
        if any(w in q for w in ["why", "reason", "analyze", "think", "step by step", "pros and cons"]):
            return "reasoning"
        return "casual"

    def get_model_info(self) -> Dict:
        return {
            "current":  self.current_model,
            "server":   self._active_server["name"] if self._active_server else "unknown",
            "available": self.available_models,
        }

    def force_set(self, model: str) -> bool:
        if model in self.available_models:
            self.current_model = model
            return True
        return False
