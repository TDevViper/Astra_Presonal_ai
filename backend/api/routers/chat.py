import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from api.deps import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()
MAX_INPUT_CHARS = 4000


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(request: Request, body: ChatRequest, _=Depends(require_api_key)):
    # Per-IP rate limit: 30 requests/minute on the heavy /chat endpoint
    user_input = body.message.strip()
    if not user_input or len(user_input) > MAX_INPUT_CHARS:
        raise HTTPException(status_code=400, detail=f"Message must be 1-{MAX_INPUT_CHARS} characters")
    try:
        from core.brain_singleton import get_brain
        brain  = get_brain()
        logger.info("💬 User: %s", user_input[:50])
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, brain.process, user_input)
        logger.info("🤖 ASTRA: %s", result["reply"][:50])
        return result
    except Exception as e:
        logger.error("chat endpoint error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
