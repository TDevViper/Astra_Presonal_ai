import sqlite3
import os
from datetime import datetime

import os as _os
DB_PATH = os.getenv("MEMORY_DB", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "astra_memory.db"))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent TEXT,
            emotion TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_exchange(user_msg: str, assistant_msg: str, intent: str = None, emotion: str = None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = datetime.now().isoformat()
    c.execute(
        "INSERT INTO conversations (timestamp, role, content, intent, emotion) VALUES (?,?,?,?,?)",
        (ts, "user", user_msg, intent, emotion)
    )
    c.execute(
        "INSERT INTO conversations (timestamp, role, content, intent, emotion) VALUES (?,?,?,?,?)",
        (ts, "assistant", assistant_msg, intent, emotion)
    )
    conn.commit()
    conn.close()

def load_recent_history(n: int = 20) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
        (n * 2,)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def save_fact(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO facts (key, value, updated_at) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_fact(key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM facts WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

if __name__ != "__main__":
    try:
        init_db()
    except Exception as _e:
        pass  # non-critical: first-run or empty db
