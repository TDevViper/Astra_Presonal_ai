"""
Auth endpoints:
  POST /auth/register
  POST /auth/login
  POST /auth/refresh
  GET  /auth/me
"""

import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth.users_db import init_db, create_user, get_user_by_id, authenticate_user
from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
_limiter = Limiter(key_func=get_remote_address)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

import os
init_db()


import threading as _threading
_rt_blacklist: set = set()
_rt_lock = _threading.Lock()

def _blacklist_token(token: str):
    try:
        import redis as _r2
        r = _r2.Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379"),socket_connect_timeout=1)
        from auth.jwt_handler import REFRESH_EXPIRE
        r.setex("rt:bl:" + token, REFRESH_EXPIRE * 86400, "1")
        return
    except Exception:
        pass
    with _rt_lock:
        _rt_blacklist.add(token)

def _is_blacklisted(token: str) -> bool:
    try:
        import redis as _r2
        r = _r2.Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379"),socket_connect_timeout=1)
        return r.exists("rt:bl:" + token) == 1
    except Exception:
        pass
    with _rt_lock:
        return token in _rt_blacklist



class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


@router.post("/register", status_code=201)
@_limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest):
    try:
        user = create_user(
            user_id=str(uuid.uuid4()),
            username=body.username,
            email=body.email,
            password=body.password,
        )
        return {"message": "User created", "username": user["username"]}
    except Exception:
        raise HTTPException(status_code=400, detail="Registration failed. Username or email may already be in use.")


@router.post("/login", response_model=TokenResponse)
@_limiter.limit("10/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    return TokenResponse(
        access_token=create_access_token(user["id"], user["username"], user["role"]),
        refresh_token=create_refresh_token(user["id"]),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    user_id = verify_refresh_token(body.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return TokenResponse(
        access_token=create_access_token(user["id"], user["username"], user["role"]),
        refresh_token=create_refresh_token(user["id"]),
    )


@router.post("/logout", status_code=200)
def logout(body: RefreshRequest):
    _blacklist_token(body.refresh_token)
    return {"message": "Logged out"}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "role": current_user["role"],
    }


@router.get("/rate-limit-status")
def rate_limit_status(current_user: dict = Depends(get_current_user)):
    from auth.rate_limiter import ROLE_LIMITS
    from collections import deque
    from auth.rate_limiter import _windows
    import time

    role = current_user["role"]
    limit = ROLE_LIMITS.get(role, 5)
    dq = _windows.get(current_user["id"], deque())
    now = time.time()
    used = sum(1 for t in dq if t > now - 60)
    return {
        "role": role,
        "limit_per_min": limit,
        "used_this_min": used,
        "remaining": max(0, limit - used),
    }
