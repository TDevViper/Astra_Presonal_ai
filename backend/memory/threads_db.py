"""
Conversation thread store — SQLite backed.
Each thread belongs to one user, has a title, and stores messages as JSON.
"""
import sqlite3
import os
import json
import logging
from typing import List, Optional, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "threads.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS threads (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                title       TEXT NOT NULL DEFAULT 'New Chat',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                is_archived INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          TEXT PRIMARY KEY,
                thread_id   TEXT NOT NULL,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads(id)
            );
            CREATE INDEX IF NOT EXISTS idx_threads_user ON threads(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
        """)
    logger.info("✅ threads DB initialised")


def create_thread(thread_id: str, user_id: str, title: str = "New Chat") -> Dict:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO threads (id, user_id, title, created_at, updated_at) VALUES (?,?,?,?,?)",
            (thread_id, user_id, title, now, now)
        )
        c.commit()
    return {"id": thread_id, "user_id": user_id, "title": title, "created_at": now}


def get_threads(user_id: str) -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM threads WHERE user_id=? AND is_archived=0 ORDER BY updated_at DESC",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_thread(thread_id: str, user_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM threads WHERE id=? AND user_id=?",
            (thread_id, user_id)
        ).fetchone()
    return dict(row) if row else None


def rename_thread(thread_id: str, user_id: str, title: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            "UPDATE threads SET title=?, updated_at=? WHERE id=? AND user_id=?",
            (title, now, thread_id, user_id)
        )
        c.commit()
    return cur.rowcount > 0


def archive_thread(thread_id: str, user_id: str) -> bool:
    with _conn() as c:
        cur = c.execute(
            "UPDATE threads SET is_archived=1 WHERE id=? AND user_id=?",
            (thread_id, user_id)
        )
        c.commit()
    return cur.rowcount > 0


def add_message(msg_id: str, thread_id: str, role: str, content: str):
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (id, thread_id, role, content, created_at) VALUES (?,?,?,?,?)",
            (msg_id, thread_id, role, content, now)
        )
        c.execute(
            "UPDATE threads SET updated_at=? WHERE id=?",
            (now, thread_id)
        )
        c.commit()


def get_messages(thread_id: str, limit: int = 50) -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM messages WHERE thread_id=? ORDER BY created_at ASC LIMIT ?",
            (thread_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def fork_thread(new_id: str, source_thread_id: str, user_id: str,
                from_message_id: str, title: str) -> Dict:
    """Branch a conversation from any message point."""
    import uuid
    msgs = get_messages(source_thread_id)
    # Find cutoff index
    cutoff = next((i for i, m in enumerate(msgs) if m["id"] == from_message_id), len(msgs))
    forked_msgs = msgs[:cutoff + 1]

    thread = create_thread(new_id, user_id, title)
    with _conn() as c:
        for m in forked_msgs:
            c.execute(
                "INSERT INTO messages (id, thread_id, role, content, created_at) VALUES (?,?,?,?,?)",
                (str(uuid.uuid4()), new_id, m["role"], m["content"], m["created_at"])
            )
        c.commit()
    return thread
