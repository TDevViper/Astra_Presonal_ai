"""
SQLite-backed user store.
Handles registration, login, password hashing.
"""

import sqlite3
import os
import logging
from typing import Optional, Dict
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.db")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                email       TEXT UNIQUE NOT NULL,
                hashed_pw   TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'user',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                is_active   INTEGER NOT NULL DEFAULT 1
            )
        """)
        c.commit()
    logger.info("✅ users DB initialised")


def create_user(
    user_id: str, username: str, email: str, password: str, role: str = "user"
) -> Dict:
    hashed = pwd_context.hash(password)
    with _conn() as c:
        c.execute(
            "INSERT INTO users (id, username, email, hashed_pw, role) VALUES (?,?,?,?,?)",
            (user_id, username, email, hashed, role),
        )
        c.commit()
    return {"id": user_id, "username": username, "email": email, "role": role}


def get_user_by_username(username: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1", (username,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM users WHERE id=? AND is_active=1", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_pw"]):
        return None
    return user
