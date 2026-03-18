"""Tests for ResponseCache — local dict fallback (no Redis needed)."""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def cache(monkeypatch):
    monkeypatch.delenv("REDIS_HOST", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:1")  # unreachable → local fallback
    from core.response_cache import ResponseCache
    return ResponseCache(ttl=2)  # 2s TTL for fast expiry tests


def _reply(text="hello", intent="general"):
    return {"reply": text, "intent": intent, "agent": "test", "emotion": "neutral",
            "confidence": 0.9, "tool_used": False, "memory_updated": False,
            "confidence_label": "HIGH", "confidence_emoji": "🟢"}


def test_cache_miss_on_empty(cache):
    assert cache.get("anything") is None


def test_set_and_get_roundtrip(cache):
    r = _reply("hi there")
    cache.set("hello", r)
    result = cache.get("hello")
    assert result is not None
    assert result["reply"] == "hi there"


def test_case_insensitive_key(cache):
    cache.set("Hello World", _reply("test"))
    assert cache.get("hello world") is not None
    assert cache.get("HELLO WORLD") is not None


def test_skips_web_search_intent(cache):
    cache.set("latest news", _reply("news", intent="web_search"))
    assert cache.get("latest news") is None


def test_skips_memory_storage_intent(cache):
    cache.set("my name is arnav", _reply("ok", intent="memory_storage"))
    assert cache.get("my name is arnav") is None


def test_skips_error_intent(cache):
    cache.set("crash", _reply("oops", intent="error"))
    assert cache.get("crash") is None


def test_ttl_expiry(cache):
    cache.set("expiring", _reply("bye"))
    assert cache.get("expiring") is not None
    time.sleep(2.1)
    assert cache.get("expiring") is None


def test_invalidate_removes_entry(cache):
    cache.set("remove me", _reply("gone"))
    cache.invalidate("remove me")
    assert cache.get("remove me") is None


def test_flush_clears_all(cache):
    cache.set("one", _reply("a"))
    cache.set("two", _reply("b"))
    cache.flush()
    assert cache.get("one") is None
    assert cache.get("two") is None


def test_stats_tracks_hits_and_misses(cache):
    cache.set("q", _reply("a"))
    cache.get("q")       # hit
    cache.get("missing") # miss
    s = cache.stats()
    assert s["hits"] == 1
    assert s["misses"] == 1
    assert s["hit_rate"] == 0.5
    assert s["backend"] in ("local", "redis")


def test_skips_long_reply(cache, monkeypatch):
    monkeypatch.setenv("CACHE_MAX_WORDS", "5")
    from core import response_cache
    monkeypatch.setattr(response_cache, "_MAX_REPLY_WORDS", 5)
    long_reply = _reply("word " * 10)
    cache.set("long question", long_reply)
    assert cache.get("long question") is None
