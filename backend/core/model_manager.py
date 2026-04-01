import logging
import os
import requests
import ollama
import time
from typing import Dict, List

logger = logging.getLogger(__name__)
import threading as _threading
import time as _time
import subprocess as _subprocess

_last_used: dict = {}
_last_used_lock = _threading.Lock()
_UNLOAD_AFTER = 300


def _auto_unload_loop():
    """Unload idle Ollama models. Start via start_auto_unload(), not at import."""
    while True:
        _time.sleep(60)
        now = _time.time()
        with _last_used_lock:
            stale = [m for m, t in _last_used.items() if now - t > _UNLOAD_AFTER]
        for model in stale:
            try:
                _subprocess.run(
                    ["ollama", "stop", model], timeout=5, capture_output=True
                )
                with _last_used_lock:
                    _last_used.pop(model, None)
                logger.info("♻️  Auto-unloaded idle model: %s", model)
            except Exception as e:
                logger.warning("unload failed %s: %s", model, e)


def start_auto_unload():
    """Call once from lifespan — not at import time."""
    _threading.Thread(
        target=_auto_unload_loop, daemon=True, name="ollama-auto-unload"
    ).start()
    logger.info("♻️  Ollama auto-unload started (idle threshold: %ds)", _UNLOAD_AFTER)


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_SERVERS = [{"name": "Local Ollama", "url": OLLAMA_HOST}]

MODEL_PROFILES = {
    "phi3:mini": {"best_for": ["casual", "memory", "greeting"], "speed": "fast"},
    "llama3.2:3b": {"best_for": ["reasoning", "analysis"], "speed": "fast"},
    "mistral:latest": {"best_for": ["technical", "coding"], "speed": "slow"},
}

INTENT_MODEL_MAP = {
    "fast": "phi3:mini",
    "casual": "phi3:mini",
    "memory": "phi3:mini",
    "greeting": "phi3:mini",
    "simple_question": "phi3:mini",
    "reasoning": "llama3.2:3b",
    "step_by_step": "llama3.2:3b",
    "analysis": "llama3.2:3b",
    "technical": "mistral:latest",
    "coding": "mistral:latest",
    "research": "mistral:latest",
    "web_search": "mistral:latest",
}

_server_cache: Dict = {}
_server_cache_time: float = 0
_SERVER_CACHE_TTL = 30

_CASUAL_EXACT = {
    "hi",
    "hey",
    "hello",
    "sup",
    "yo",
    "hiya",
    "howdy",
    "what is up",
    "what's up",
    "whats up",
    "wassup",
    "how are you",
    "how r u",
    "how are u",
    "good morning",
    "good evening",
    "good afternoon",
    "good night",
    "bye",
    "goodbye",
    "see ya",
    "later",
    "thanks",
    "thank you",
    "ty",
    "ok",
    "okay",
    "cool",
    "nice",
    "great",
    "awesome",
    "lol",
    "haha",
    "hmm",
}
_CASUAL_STARTS = (
    "hey ",
    "hi ",
    "hello ",
    "what's up",
    "whats up",
    "how are",
    "good morning",
    "good night",
)


def _check_server(url: str, timeout: int = 1) -> bool:
    try:
        return requests.get(url, timeout=timeout).status_code == 200
    except Exception:
        return False


def _get_active_server() -> Dict:
    global _server_cache, _server_cache_time
    now = time.time()
    if _server_cache and now - _server_cache_time < _SERVER_CACHE_TTL:
        return _server_cache
    for server in OLLAMA_SERVERS:
        if _check_server(server["url"]):
            logger.info(f"✅ Using: {server['name']} ({server['url']})")
            _server_cache = server
            _server_cache_time = now
            return server
    logger.warning("⚠️  No Ollama server — run: ollama serve")
    _server_cache = OLLAMA_SERVERS[-1]
    _server_cache_time = now
    return OLLAMA_SERVERS[-1]


class ModelManager:
    def __init__(self, default_model: str = "phi3:mini"):
        self.default_model = default_model
        self.current_model = default_model
        self._active_server = None
        self._ollama_host = OLLAMA_HOST
        self._refresh_server()

    def _refresh_server(self):
        self._active_server = _get_active_server()
        self._ollama_host = self._active_server["url"]  # instance var, not os.environ
        self.available_models = self._get_available_models()
        logger.info(f"🖥️  Models: {self.available_models}")

    def _get_available_models(self) -> List[str]:
        try:
            client = ollama.Client(host=getattr(self, "_ollama_host", OLLAMA_HOST))
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
        global _server_cache_time
        if time.time() - _server_cache_time > _SERVER_CACHE_TTL:
            if not _check_server(getattr(self, "_ollama_host", OLLAMA_HOST), timeout=1):
                self._refresh_server()
        preferred = INTENT_MODEL_MAP.get(intent, self.default_model)
        if preferred in self.available_models:
            self.current_model = preferred
            with _last_used_lock:
                _last_used[preferred] = _time.time()
            return preferred
        for model in ["phi3:mini", "llama3.2:3b", "mistral:latest"]:
            if model in self.available_models:
                logger.warning(f"⚠️  Fallback: {model}")
                self.current_model = model
                return model
        return self.default_model

    def classify_query_intent(self, query: str) -> str:
        q = query.lower().strip()
        wc = len(q.split())

        # 1. Casual — checked FIRST before any keyword matching
        if q in _CASUAL_EXACT:
            return "casual"
        if q.startswith(_CASUAL_STARTS):
            return "casual"

        # 1.5 Memory storage — catch before other intents
        if any(
            p in q
            for p in [
                "my name is",
                "i live in",
                "i am from",
                "i work at",
                "i prefer",
                "remember that",
                "my age is",
                "i like",
                "i dislike",
                "i hate",
                "my job",
                "i study",
            ]
        ):
            return "memory"

        # 2. Coding
        if any(
            w in q
            for w in [
                "```",
                "def ",
                "class ",
                "import ",
                "function(",
                "debug",
                "traceback",
                "compile",
                "algorithm",
                "implement",
                "refactor",
            ]
        ):
            return "coding"
        if any(w in q for w in ["code", "bug", "error"]) and wc > 3:
            return "coding"

        # 3. Research
        if any(
            w in q
            for w in [
                "search",
                "google",
                "find",
                "latest",
                "news",
                "current",
                "today",
                "recent",
                "price",
                "weather",
            ]
        ):
            return "research"

        # 4. Reasoning
        if any(
            w in q
            for w in [
                "why",
                "reason",
                "analyze",
                "pros and cons",
                "step by step",
                "should i",
                "tradeoff",
            ]
        ):
            return "reasoning"

        # 5. Technical — only longer substantive queries
        if wc >= 5 and any(
            w in q
            for w in [
                "explain",
                "how does",
                "what is",
                "difference between",
                "compare",
                "tell me about",
                "how do",
                "how can",
                "who is",
                "when was",
                "where is",
                "optimize",
                "capital",
                "history",
            ]
        ):
            return "technical"

        # 6. Short queries → casual
        if wc <= 4:
            return "casual"

        return "technical"

    def get_model_info(self) -> Dict:
        return {
            "current": self.current_model,
            "server": self._active_server["name"] if self._active_server else "unknown",
            "available": self.available_models,
        }

    def force_set(self, model: str) -> bool:
        if model in self.available_models:
            self.current_model = model
            return True
        return False
