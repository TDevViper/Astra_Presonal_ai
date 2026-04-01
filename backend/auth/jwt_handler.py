"""
JWT creation and verification.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from jose import JWTError, jwt

logger = logging.getLogger(__name__)

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY env var is not set — refusing to start.")
ALGORITHM = "HS256"
ACCESS_EXPIRE = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "60"))
REFRESH_EXPIRE = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7"))


def create_access_token(user_id: str, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_EXPIRE)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed: %s", e)
        return None


def verify_access_token(token: str) -> Optional[Dict]:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    return payload


def verify_refresh_token(token: str) -> Optional[str]:
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    return payload.get("sub")
