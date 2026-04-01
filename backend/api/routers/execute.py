from auth.rbac import require_permission

"""
api/routers/execute.py — Tool execution endpoint (FastAPI).

Security fix: dangerous tools require a server-issued approval token
(HMAC-signed, 60s TTL) instead of client-supplied approved=true.
"""
import hashlib
import hmac
import json
import logging
import os
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from api.deps import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()

DANGEROUS = {"python_sandbox", "git_tool", "file_reader"}
_TOKEN_TTL = 60  # seconds
_SECRET = os.getenv("ASTRA_API_KEY", "dev-secret").encode()


def _issue_token(tool_name: str, params_hash: str) -> str:
    """Issue a server-side approval token valid for 60 seconds."""
    expires = int(time.time()) + _TOKEN_TTL
    payload = f"{tool_name}:{params_hash}:{expires}"
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{expires}:{sig}"


def _verify_token(token: str, tool_name: str, params_hash: str) -> bool:
    """Verify approval token is valid and not expired."""
    try:
        expires_str, sig = token.split(":", 1)
        expires = int(expires_str)
        if time.time() > expires:
            return False
        payload = f"{tool_name}:{params_hash}:{expires}"
        expected = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:16]
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


class ExecuteRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}
    approval_token: Optional[str] = None  # server-issued token, not a boolean


class CapabilityUpdate(BaseModel):
    enabled: bool


@router.get("/capabilities")
async def get_capabilities(_=Depends(require_api_key)):
    try:
        from core.brain_singleton import get_brain

        return get_brain().capabilities.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/capabilities/{capability}")
async def toggle_capability(
    capability: str, body: CapabilityUpdate, _=Depends(require_api_key)
):
    try:
        from core.brain_singleton import get_brain

        brain = get_brain()
        success = (
            brain.capabilities.enable(capability)
            if body.enabled
            else brain.capabilities.disable(capability)
        )
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Unknown capability: {capability}"
            )
        return {"capability": capability, "enabled": body.enabled, "status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_tool(body: ExecuteRequest, _=Depends(require_api_key)):
    tool_name = body.tool
    params = body.params
    params_hash = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode()
    ).hexdigest()[:16]

    if tool_name in DANGEROUS:
        if not body.approval_token:
            # Issue a server-side token — client must send this back to confirm
            token = _issue_token(tool_name, params_hash)
            return {
                "status": "approval_required",
                "tool": tool_name,
                "approval_token": token,
                "expires_in": _TOKEN_TTL,
                "message": f"Send this approval_token back within {_TOKEN_TTL}s to confirm execution.",
            }
        if not _verify_token(body.approval_token, tool_name, params_hash):
            raise HTTPException(
                status_code=403,
                detail="Invalid or expired approval token. Request a new one.",
            )

    try:
        from tools.tool_router import ToolRouter

        result = ToolRouter().execute(tool_name, params)
        return {"status": "success", "tool": tool_name, "result": result}
    except Exception as e:
        logger.error("execute_tool error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
