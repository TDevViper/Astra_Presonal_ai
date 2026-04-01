"""
Usage dashboard endpoints — admin/owner only except /dashboard/me.
  GET /dashboard/me              my own stats
  GET /dashboard/users           all users stats (admin+)
  GET /dashboard/endpoints       endpoint breakdown (admin+)
  GET /dashboard/hourly          hourly traffic (admin+)
"""

import logging
from fastapi import APIRouter, Depends, Query
from auth.rbac import get_current_user, require_permission
from auth.usage_tracker import (
    get_user_stats,
    get_all_users_stats,
    get_endpoint_stats,
    get_hourly_breakdown,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/me")
def my_stats(
    days: int = Query(default=30, ge=1, le=90), current_user=Depends(get_current_user)
):
    stats = get_user_stats(current_user["id"], days)
    return {
        "user": current_user["username"],
        "role": current_user["role"],
        "period": f"last {days} days",
        "stats": stats,
    }


@router.get("/users")
def all_users_stats(
    days: int = Query(default=30, ge=1, le=90),
    _=Depends(require_permission("system_stats")),
):
    return {
        "period": f"last {days} days",
        "users": get_all_users_stats(days),
    }


@router.get("/endpoints")
def endpoint_stats(
    days: int = Query(default=7, ge=1, le=30),
    _=Depends(require_permission("system_stats")),
):
    return {
        "period": f"last {days} days",
        "endpoints": get_endpoint_stats(days),
    }


@router.get("/hourly")
def hourly_stats(
    days: int = Query(default=7, ge=1, le=30),
    user_id: str = Query(default=None),
    _=Depends(require_permission("system_stats")),
):
    return {
        "period": f"last {days} days",
        "hourly": get_hourly_breakdown(user_id, days),
    }
