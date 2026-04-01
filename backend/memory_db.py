import sqlite3
import os
import threading
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.getenv(
    "MEMORY_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "astra_memory.db"),
)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


@contextmanager
def get_conn():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                intent    TEXT,
                emotion   TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                key        TEXT UNIQUE NOT NULL,
                value      TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_id ON conversations(id)")


def save_exchange(
    user_msg: str, assistant_msg: str, intent: str = None, emotion: str = None
):
    ts = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (timestamp, role, content, intent, emotion) VALUES (?,?,?,?,?)",
            (ts, "user", user_msg, intent, emotion),
        )
        conn.execute(
            "INSERT INTO conversations (timestamp, role, content, intent, emotion) VALUES (?,?,?,?,?)",
            (ts, "assistant", assistant_msg, intent, emotion),
        )


def load_recent_history(n: int = 20) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?", (n * 2,)
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def save_fact(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO facts (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, datetime.now().isoformat()),
        )


def get_fact(key: str):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


if __name__ != "__main__":
    try:
        init_db()
    except Exception as _e:
        pass
