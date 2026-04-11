"""
Role-Based Access Control
Roles (highest to lowest): owner > admin > user > guest
"""

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from auth.users_db import get_user_by_id
from auth.jwt_handler import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── Role hierarchy ────────────────────────────────────────────────────────────
ROLE_RANK = {"guest": 0, "user": 1, "admin": 2, "owner": 3}

# ── Permission matrix ─────────────────────────────────────────────────────────
PERMISSIONS = {
    "chat": ["guest", "user", "admin", "owner"],
    "memory_read": ["user", "admin", "owner"],
    "memory_write": ["user", "admin", "owner"],
    "memory_wipe": ["admin", "owner"],
    "execute_python": ["user", "admin", "owner"],
    "execute_shell": ["admin", "owner"],
    "execute_shell_root": ["owner"],
    "model_select": ["admin", "owner"],
    "user_manage": ["admin", "owner"],
    "user_delete": ["owner"],
    "system_stats": ["admin", "owner"],
    "ingest_knowledge": ["admin", "owner"],
    "view_traces": ["admin", "owner"],
}


def get_current_user(token: str = Depends(oauth2_scheme), request: Request = None) -> dict:
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
    if request is not None:
        request.state.current_user = user
    return user


def require_permission(permission: str):
    """FastAPI dependency — raises 403 if user lacks permission."""

    def _check(current_user: dict = Depends(get_current_user)):
        allowed_roles = PERMISSIONS.get(permission, [])
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' cannot perform '{permission}'",
            )
        return current_user

    return _check


def require_role(minimum_role: str):
    """FastAPI dependency — requires minimum role rank."""

    def _check(current_user: dict = Depends(get_current_user)):
        user_rank = ROLE_RANK.get(current_user["role"], 0)
        required_rank = ROLE_RANK.get(minimum_role, 999)
        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires '{minimum_role}' role or higher",
            )
        return current_user

    return _check
