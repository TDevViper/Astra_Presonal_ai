import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from api.deps import require_api_key
from auth.rate_limiter import rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()
MAX_INPUT_CHARS = 4000


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(request: Request, body: ChatRequest, _=Depends(require_api_key)):
    user_input = body.message.strip()
    if not user_input or len(user_input) > MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=400, detail=f"Message must be 1-{MAX_INPUT_CHARS} characters"
        )
    _INJ = ("ignore previous instructions","ignore all instructions","disregard your system prompt","you are now","new instructions:","[system]","###instruction")
    if any(p in user_input.lower() for p in _INJ):
        raise HTTPException(status_code=400, detail="Message contains disallowed content")
    try:
        from core.brain_singleton import get_brain, load_request_history

        brain = get_brain()
        history = load_request_history(n=15)
        # Session scoped to API key — prevents cross-user cache leakage
        # Use JWT sub as session scope to prevent cross-user cache leaks
        _auth = request.headers.get("Authorization", "")
        _jwt_sub = ""
        if _auth.startswith("Bearer "):
            try:
                from auth.jwt_handler import verify_access_token
                _pl = verify_access_token(_auth[7:])
                _jwt_sub = _pl.get("sub", "") if _pl else ""
            except Exception:
                pass
        session_id = (_jwt_sub or request.headers.get("X-API-Key", "default"))[:32]
        logger.info("💬 User: %s", user_input[:50])
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: brain.process(user_input, history=history, session_id=session_id),
        )
        logger.info("🤖 ASTRA: %s", result["reply"][:50])
        return result
    except Exception as e:
        logger.error("chat endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
