"""
memory_db.py — Single SQLite persistence layer for all ASTRA memory.
Replaces JSON file storage. All memory reads/writes go here.
"""
import sqlite3
import os
import json
import threading
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.getenv(
    "MEMORY_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "astra_memory.db"),
)

_local = threading.local()
_SCHEMA_VERSION = 2


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
                user_id   TEXT NOT NULL DEFAULT 'default',
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                intent    TEXT,
                emotion   TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL DEFAULT 'default',
                key        TEXT NOT NULL,
                value      TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id  TEXT PRIMARY KEY,
                name     TEXT DEFAULT 'User',
                location TEXT,
                data     TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emotion_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT NOT NULL DEFAULT 'default',
                label     TEXT NOT NULL,
                score     REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL DEFAULT 'default',
                summary    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_id ON conversations(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_emotion_user ON emotion_log(user_id)")
        conn.execute("PRAGMA user_version = {}".format(_SCHEMA_VERSION))
    logger.info("memory_db initialized (schema v%d)", _SCHEMA_VERSION)


def save_exchange(user_msg: str, assistant_msg: str, intent: str = None, emotion: str = None, user_id: str = "default"):
    ts = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO conversations (timestamp,user_id,role,content,intent,emotion) VALUES (?,?,?,?,?,?)",
                     (ts, user_id, "user", user_msg, intent, emotion))
        conn.execute("INSERT INTO conversations (timestamp,user_id,role,content,intent,emotion) VALUES (?,?,?,?,?,?)",
                     (ts, user_id, "assistant", assistant_msg, intent, emotion))


def load_recent_history(n: int = 20, user_id: str = "default") -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, n * 2)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def save_fact(key: str, value: str, user_id: str = "default"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO facts (user_id,key,value,updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (user_id, key, value, datetime.now().isoformat()))


def get_fact(key: str, user_id: str = "default") -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM facts WHERE user_id=? AND key=?", (user_id, key)).fetchone()
    return row[0] if row else None


def get_all_facts(user_id: str = "default") -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM facts WHERE user_id=? ORDER BY updated_at DESC", (user_id,)).fetchall()
    return [{"type": r[0], "value": r[1]} for r in rows]


def get_prefs(user_id: str = "default") -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT name, location, data FROM user_prefs WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return {"name": "User", "location": None}
    prefs = {"name": row[0], "location": row[1]}
    try:
        prefs.update(json.loads(row[2] or "{}"))
    except Exception:
        pass
    return prefs


def save_prefs(prefs: Dict[str, Any], user_id: str = "default"):
    prefs = dict(prefs)
    name = prefs.pop("name", "User")
    location = prefs.pop("location", None)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_prefs (user_id,name,location,data) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET name=excluded.name,location=excluded.location,data=excluded.data",
            (user_id, name, location, json.dumps(prefs)))


def log_emotion(label: str, score: float, user_id: str = "default"):
    with get_conn() as conn:
        conn.execute("INSERT INTO emotion_log (user_id,label,score,timestamp) VALUES (?,?,?,?)",
                     (user_id, label, score, datetime.now().isoformat()))
    with get_conn() as conn:
        conn.execute("""DELETE FROM emotion_log WHERE user_id=? AND id NOT IN (
            SELECT id FROM emotion_log WHERE user_id=? ORDER BY id DESC LIMIT 100)""", (user_id, user_id))


def get_last_emotion(user_id: str = "default") -> Dict:
    with get_conn() as conn:
        row = conn.execute("SELECT label, score FROM emotion_log WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    return {"label": row[0], "score": row[1]} if row else {"label": "neutral", "score": 0.0}


def save_summary(summary: str, user_id: str = "default"):
    with get_conn() as conn:
        conn.execute("INSERT INTO summaries (user_id,summary,created_at) VALUES (?,?,?)",
                     (user_id, summary, datetime.now().isoformat()))


def get_summaries(n: int = 5, user_id: str = "default") -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT summary FROM summaries WHERE user_id=? ORDER BY id DESC LIMIT ?",
                            (user_id, n)).fetchall()
    return [r[0] for r in rows]


def load_memory(user_id: str = "default") -> Dict[str, Any]:
    prefs = get_prefs(user_id)
    facts = get_all_facts(user_id)
    last_emotion = get_last_emotion(user_id)
    summaries = get_summaries(user_id=user_id)
    return {
        "user_facts": facts,
        "preferences": prefs,
        "conversation_summary": summaries,
        "emotional_patterns": {
            "last_emotion": last_emotion,
            "history": [],
            "emotion_stats": {},
        },
    }


def save_memory(memory: Dict[str, Any], user_id: str = "default", history: list = None) -> bool:
    try:
        save_prefs(dict(memory.get("preferences", {})), user_id)
        for fact in memory.get("user_facts", []):
            if isinstance(fact, dict) and "type" in fact and "value" in fact:
                save_fact(fact["type"], str(fact["value"]), user_id)
        ep = memory.get("emotional_patterns", {})
        last = ep.get("last_emotion", {})
        if last.get("label"):
            log_emotion(last["label"], last.get("score", 0.0), user_id)
        for s in memory.get("conversation_summary", []):
            if isinstance(s, str) and s:
                save_summary(s, user_id)
        return True
    except Exception as e:
        logger.error("save_memory failed user=%s: %s", user_id, e)
        return False


if __name__ != "__main__":
    try:
        init_db()
    except Exception as _e:
        logger.warning("memory_db init failed: %s", _e)
