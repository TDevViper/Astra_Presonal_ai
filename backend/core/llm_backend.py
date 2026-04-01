"""
core/llm_backend.py — Abstract LLM backend interface.
Sync + async implementations for Ollama.
"""
from __future__ import annotations
import logging
import os
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Generator, List

logger = logging.getLogger(__name__)


class LLMBackend(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict], model: str, options: Dict = None) -> str: ...
    @abstractmethod
    def stream(self, messages: List[Dict], model: str, options: Dict = None) -> Generator[str, None, None]: ...
    @abstractmethod
    async def achat(self, messages: List[Dict], model: str, options: Dict = None) -> str: ...
    @abstractmethod
    async def astream(self, messages: List[Dict], model: str, options: Dict = None) -> AsyncGenerator[str, None]: ...
    @abstractmethod
    def list_models(self) -> List[str]: ...
    @abstractmethod
    def is_available(self) -> bool: ...


class OllamaBackend(LLMBackend):
    def __init__(self, host: str = None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def _client(self):
        import ollama
        return ollama.Client(host=self.host)

    def _async_client(self):
        import ollama
        return ollama.AsyncClient(host=self.host)

    def chat(self, messages: List[Dict], model: str, options: Dict = None) -> str:
        try:
            resp = self._client().chat(model=model, messages=messages,
                                       options=options or {"temperature": 0.65, "num_predict": 200})
            return resp["message"]["content"]
        except Exception as e:
            if "Connection refused" in str(e) or "Errno 61" in str(e):
                return "⚠️ Ollama is offline. Please run `ollama serve`."
            logger.error("OllamaBackend.chat error: %s", e)
            return "I can't reach my model right now."

    def stream(self, messages: List[Dict], model: str, options: Dict = None) -> Generator[str, None, None]:
        try:
            for chunk in self._client().chat(model=model, messages=messages, stream=True,
                                              options=options or {"temperature": 0.7, "num_predict": 200}):
                token = chunk["message"]["content"]
                if token:
                    yield token
        except Exception as e:
            if "Connection refused" in str(e) or "Errno 61" in str(e):
                yield "⚠️ Ollama is offline. Please run `ollama serve`."
            else:
                logger.error("OllamaBackend.stream error: %s", e)
                yield f"Error: {e}"

    async def achat(self, messages: List[Dict], model: str, options: Dict = None) -> str:
        try:
            resp = await self._async_client().chat(model=model, messages=messages,
                                                    options=options or {"temperature": 0.65, "num_predict": 200})
            return resp["message"]["content"]
        except Exception as e:
            if "Connection refused" in str(e) or "Errno 61" in str(e):
                return "⚠️ Ollama is offline. Please run `ollama serve`."
            logger.error("OllamaBackend.achat error: %s", e)
            return "I can't reach my model right now."

    async def astream(self, messages: List[Dict], model: str, options: Dict = None) -> AsyncGenerator[str, None]:
        try:
            async for chunk in await self._async_client().chat(
                model=model, messages=messages, stream=True,
                options=options or {"temperature": 0.7, "num_predict": 200}
            ):
                token = chunk["message"]["content"]
                if token:
                    yield token
        except Exception as e:
            if "Connection refused" in str(e) or "Errno 61" in str(e):
                yield "⚠️ Ollama is offline. Please run `ollama serve`."
            else:
                logger.error("OllamaBackend.astream error: %s", e)
                yield f"Error: {e}"

    def list_models(self) -> List[str]:
        try:
            result = self._client().list()
            return [m.get("model", m.get("name", "")) for m in result.get("models", [])]
        except Exception:
            return []

    def is_available(self) -> bool:
        try:
            import requests
            return requests.get(self.host, timeout=1).status_code == 200
        except Exception:
            return False


class StubBackend(LLMBackend):
    def __init__(self, reply: str = "mocked llm reply"):
        self._reply = reply

    def chat(self, messages, model, options=None) -> str:
        return self._reply

    def stream(self, messages, model, options=None):
        for word in self._reply.split():
            yield word + " "

    async def achat(self, messages, model, options=None) -> str:
        return self._reply

    async def astream(self, messages, model, options=None):
        for word in self._reply.split():
            yield word + " "

    def list_models(self) -> List[str]:
        return ["stub-model"]

    def is_available(self) -> bool:
        return True


_default_backend: LLMBackend = None


def get_backend() -> LLMBackend:
    global _default_backend
    if _default_backend is None:
        _default_backend = OllamaBackend()
    return _default_backend


def set_backend(backend: LLMBackend):
    global _default_backend
    _default_backend = backend
    logger.info("LLM backend set to: %s", type(backend).__name__)
