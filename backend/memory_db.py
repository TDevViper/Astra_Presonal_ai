"""
memory_db.py — SQLite-backed conversation history and facts store.
Uses WAL mode and thread-local connections for concurrency safety.
"""
import sqlite3
import threading
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "memory.db")

_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        c = sqlite3.connect(DB_PATH, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        _local.conn = c
    return _local.conn


def init_db():
    c = _conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            role      TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            intent    TEXT,
            ts        REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            key       TEXT PRIMARY KEY,
            value     TEXT NOT NULL,
            updated   REAL NOT NULL DEFAULT (unixepoch('now', 'subsec'))
        )
    """)
    c.commit()


def save_exchange(user_msg: str, assistant_msg: str, intent: str = None):
    c = _conn()
    c.execute(
        "INSERT INTO conversations (role, content, intent) VALUES (?, ?, ?)",
        ("user", user_msg, intent),
    )
    c.execute(
        "INSERT INTO conversations (role, content, intent) VALUES (?, ?, ?)",
        ("assistant", assistant_msg, intent),
    )
    c.commit()


def load_recent_history(n: int = 15) -> list:
    c = _conn()
    rows = c.execute(
        """
        SELECT role, content FROM (
            SELECT id, role, content FROM conversations
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
        """,
        (n,),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def save_fact(key: str, value: str):
    c = _conn()
    c.execute(
        "INSERT INTO facts (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=unixepoch('now','subsec')",
        (key, value),
    )
    c.commit()


def get_fact(key: str) -> Optional[str]:
    c = _conn()
    row = c.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None
