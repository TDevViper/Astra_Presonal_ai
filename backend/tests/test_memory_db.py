"""Tests for memory_db — WAL mode, save/load, facts."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    import memory_db
    db = str(tmp_path / "test.db")
    monkeypatch.setattr(memory_db, "DB_PATH", db)
    # Reset thread-local connection so each test gets a fresh DB
    if hasattr(memory_db._local, "conn"):
        try:
            memory_db._local.conn.close()
        except Exception:
            pass
        memory_db._local.conn = None
    memory_db.init_db()
    yield db
    # Cleanup
    if hasattr(memory_db._local, "conn") and memory_db._local.conn:
        try:
            memory_db._local.conn.close()
        except Exception:
            pass
        memory_db._local.conn = None


def test_init_creates_tables(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "conversations" in tables
    assert "facts" in tables


def test_wal_mode_enabled(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"


def test_save_and_load_exchange(tmp_db):
    import memory_db
    memory_db.save_exchange("hello", "hi there", intent="greeting")
    history = memory_db.load_recent_history(n=5)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "hello"
    assert history[1]["role"] == "assistant"


def test_load_history_order_is_chronological(tmp_db):
    import memory_db
    memory_db.save_exchange("first", "reply1")
    memory_db.save_exchange("second", "reply2")
    history = memory_db.load_recent_history(n=10)
    contents = [h["content"] for h in history]
    assert contents.index("first") < contents.index("second")


def test_save_and_get_fact(tmp_db):
    import memory_db
    memory_db.save_fact("city", "Delhi")
    assert memory_db.get_fact("city") == "Delhi"


def test_save_fact_upserts(tmp_db):
    import memory_db
    memory_db.save_fact("city", "Delhi")
    memory_db.save_fact("city", "Mumbai")
    assert memory_db.get_fact("city") == "Mumbai"


def test_get_fact_missing_returns_none(tmp_db):
    import memory_db
    assert memory_db.get_fact("nonexistent") is None
