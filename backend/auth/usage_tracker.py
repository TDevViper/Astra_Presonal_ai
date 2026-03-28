"""
Per-user usage tracking.
Logs every request: endpoint, tokens, response time, status.
"""
import sqlite3, os, time, logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "usage.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id            TEXT PRIMARY KEY,
                user_id       TEXT NOT NULL,
                username      TEXT NOT NULL,
                role          TEXT NOT NULL,
                endpoint      TEXT NOT NULL,
                method        TEXT NOT NULL,
                status_code   INTEGER,
                duration_ms   REAL,
                tokens_in     INTEGER DEFAULT 0,
                tokens_out    INTEGER DEFAULT 0,
                model         TEXT DEFAULT '',
                created_at    TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_usage_time ON usage_events(created_at);
        """)
    logger.info("✅ usage DB initialised")


def log_event(user_id: str, username: str, role: str, endpoint: str,
              method: str, status_code: int, duration_ms: float,
              tokens_in: int = 0, tokens_out: int = 0, model: str = ""):
    import uuid
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute("""
            INSERT INTO usage_events
            (id, user_id, username, role, endpoint, method, status_code,
             duration_ms, tokens_in, tokens_out, model, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (str(uuid.uuid4()), user_id, username, role, endpoint,
              method, status_code, duration_ms, tokens_in, tokens_out, model, now))
        c.commit()


def get_user_stats(user_id: str, days: int = 30) -> Dict:
    with _conn() as c:
        row = c.execute("""
            SELECT
                COUNT(*)                          as total_requests,
                SUM(tokens_in + tokens_out)       as total_tokens,
                AVG(duration_ms)                  as avg_duration_ms,
                SUM(CASE WHEN status_code=429 THEN 1 ELSE 0 END) as rate_limited,
                SUM(CASE WHEN status_code>=500 THEN 1 ELSE 0 END) as errors
            FROM usage_events
            WHERE user_id=?
            AND created_at >= datetime('now', ?)
        """, (user_id, f"-{days} days")).fetchone()
    return dict(row) if row else {}


def get_all_users_stats(days: int = 30) -> List[Dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT
                user_id,
                username,
                role,
                COUNT(*)                          as total_requests,
                SUM(tokens_in + tokens_out)       as total_tokens,
                AVG(duration_ms)                  as avg_duration_ms,
                SUM(CASE WHEN status_code=429 THEN 1 ELSE 0 END) as rate_limited,
                SUM(CASE WHEN status_code>=500 THEN 1 ELSE 0 END) as errors,
                MAX(created_at)                   as last_active
            FROM usage_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY user_id
            ORDER BY total_requests DESC
        """, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


def get_endpoint_stats(days: int = 7) -> List[Dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT
                endpoint,
                method,
                COUNT(*)            as total_calls,
                AVG(duration_ms)    as avg_duration_ms,
                MAX(duration_ms)    as max_duration_ms,
                SUM(CASE WHEN status_code>=400 THEN 1 ELSE 0 END) as errors
            FROM usage_events
            WHERE created_at >= datetime('now', ?)
            GROUP BY endpoint, method
            ORDER BY total_calls DESC
        """, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]


def get_hourly_breakdown(user_id: Optional[str] = None, days: int = 7) -> List[Dict]:
    with _conn() as c:
        if user_id:
            rows = c.execute("""
                SELECT
                    strftime('%Y-%m-%d %H:00', created_at) as hour,
                    COUNT(*) as requests,
                    SUM(tokens_in + tokens_out) as tokens
                FROM usage_events
                WHERE user_id=? AND created_at >= datetime('now', ?)
                GROUP BY hour ORDER BY hour ASC
            """, (user_id, f"-{days} days")).fetchall()
        else:
            rows = c.execute("""
                SELECT
                    strftime('%Y-%m-%d %H:00', created_at) as hour,
                    COUNT(*) as requests,
                    SUM(tokens_in + tokens_out) as tokens
                FROM usage_events
                WHERE created_at >= datetime('now', ?)
                GROUP BY hour ORDER BY hour ASC
            """, (f"-{days} days",)).fetchall()
    return [dict(r) for r in rows]
