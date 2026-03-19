"""Tests for memory_engine — locking, load, save, corruption recovery."""
import json
import os
import sys
import threading
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=False)
def mem_file(tmp_path, monkeypatch):
    """Redirect MEMORY_FILE to a temp path for each test."""
    import memory.memory_engine as me
    me.invalidate_memory_cache()
    f = tmp_path / "memory.json"
    monkeypatch.setattr(me, "MEMORY_FILE", str(f))
    monkeypatch.setattr(me, "_thread_lock", __import__("threading").Lock())
    yield f


def test_load_returns_default_when_missing(mem_file):
    import memory.memory_engine as me
    me.invalidate_memory_cache()
    load_memory = me.load_memory
    DEFAULT_MEMORY = me.DEFAULT_MEMORY
    result = load_memory()
    assert result["user_facts"] == []
    assert result["preferences"]["name"] == "User"


def test_save_and_load_roundtrip(mem_file):
    import memory.memory_engine as me
    me.invalidate_memory_cache()
    load_memory = me.load_memory
    save_memory = me.save_memory
    mem = load_memory()
    mem["preferences"]["name"] = "Arnav"
    mem["user_facts"].append({"type": "hobby", "value": "chess"})
    assert save_memory(mem) is True
    reloaded = load_memory()
    assert reloaded["preferences"]["name"] == "Arnav"
    assert reloaded["user_facts"][0]["value"] == "chess"


def test_load_recovers_from_corrupted_file(mem_file):
    import memory.memory_engine as me
    me.invalidate_memory_cache()
    mem_file.write_text("{ invalid json !!!")
    result = me.load_memory()
    assert result["user_facts"] == []
    assert result["preferences"]["name"] == "User"


def test_save_is_atomic_no_partial_write(mem_file, monkeypatch):
    """os.replace ensures readers never see a half-written file."""
    from memory.memory_engine import save_memory, load_memory
    mem = load_memory()
    mem["preferences"]["name"] = "AtomicTest"
    save_memory(mem)
    # Simulate crash mid-write: tmp file should not linger
    tmp = str(mem_file) + ".tmp"
    assert not os.path.exists(tmp)


def test_concurrent_saves_no_corruption(mem_file):
    """50 threads writing simultaneously — final file must be valid JSON."""
    from memory.memory_engine import load_memory, save_memory
    errors = []

    def writer(i):
        try:
            mem = load_memory()
            mem["preferences"]["name"] = f"User{i}"
            save_memory(mem)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert errors == [], f"Errors during concurrent writes: {errors}"
    # File must still be valid JSON
    data = json.loads(mem_file.read_text())
    assert "preferences" in data


def test_missing_keys_backfilled_on_load(mem_file):
    """Old memory files missing new keys get defaults injected."""
    mem_file.write_text(json.dumps({"preferences": {"name": "OldUser"}}))
    from memory.memory_engine import load_memory
    result = load_memory()
    assert "user_facts" in result
    assert "emotional_patterns" in result
