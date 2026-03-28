"""
User management endpoints — admin/owner only.
  GET    /users/          list all users
  PATCH  /users/{id}/role change role
  DELETE /users/{id}      deactivate user
"""
import logging
import sqlite3
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth.rbac import require_permission, require_role, ROLE_RANK
from auth.users_db import DB_PATH

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


class RoleUpdate(BaseModel):
    role: str


@router.get("/")
def list_users(current_user=Depends(require_permission("user_manage"))):
    with _conn() as c:
        rows = c.execute(
            "SELECT id, username, email, role, created_at, is_active FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@router.patch("/{user_id}/role")
def update_role(user_id: str, body: RoleUpdate,
                current_user=Depends(require_permission("user_manage"))):
    if body.role not in ROLE_RANK:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    # Prevent privilege escalation — cannot assign role higher than your own
    if ROLE_RANK[body.role] >= ROLE_RANK[current_user["role"]]:
        raise HTTPException(status_code=403,
                            detail="Cannot assign a role equal to or higher than your own")
    with _conn() as c:
        c.execute("UPDATE users SET role=? WHERE id=?", (body.role, user_id))
        c.commit()
    return {"message": f"Role updated to {body.role}"}


@router.delete("/{user_id}")
def deactivate_user(user_id: str,
                    current_user=Depends(require_permission("user_delete"))):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    with _conn() as c:
        c.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        c.commit()
    return {"message": "User deactivated"}
