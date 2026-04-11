"""
memory_db.py — SQLite-backed conversation history and facts store.
Uses WAL mode and thread-local connections for concurrency safety.
Scoped per user_id.
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
            user_id   TEXT    NOT NULL DEFAULT 'default',
            role      TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            intent    TEXT,
            ts        REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_conv_user_ts ON conversations(user_id, ts)")
    c.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            user_id   TEXT    NOT NULL DEFAULT 'default',
            key       TEXT    NOT NULL,
            value     TEXT    NOT NULL,
            updated   REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec')),
            PRIMARY KEY (user_id, key)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id)")
    c.commit()


def save_exchange(user_msg: str, assistant_msg: str, intent: str = None, user_id: str = "default"):
    c = _conn()
    c.execute(
        "INSERT INTO conversations (user_id, role, content, intent) VALUES (?, ?, ?, ?)",
        (user_id, "user", user_msg, intent),
    )
    c.execute(
        "INSERT INTO conversations (user_id, role, content, intent) VALUES (?, ?, ?, ?)",
        (user_id, "assistant", assistant_msg, intent),
    )
    c.commit()


def load_recent_history(n: int = 15, user_id: str = "default") -> list:
    c = _conn()
    rows = c.execute(
        """
        SELECT role, content FROM (
            SELECT id, role, content FROM conversations
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
        """,
        (user_id, n),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def save_fact(key: str, value: str, user_id: str = "default"):
    c = _conn()
    c.execute(
        "INSERT INTO facts (user_id, key, value) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value, updated=unixepoch('now','subsec')",
        (user_id, key, value),
    )
    c.commit()


def get_fact(key: str, user_id: str = "default") -> Optional[str]:
    c = _conn()
    row = c.execute("SELECT value FROM facts WHERE user_id=? AND key=?", (user_id, key)).fetchone()
    return row["value"] if row else None
