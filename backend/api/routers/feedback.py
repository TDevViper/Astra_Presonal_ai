"""
api/routers/feedback.py — Thumbs up/down feedback endpoint.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: str
    user_input: str
    reply: str
    rating: str              # "up" or "down"
    intent: str = "general"
    comment: Optional[str] = ""
    confidence: float = 0.0


@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest):
    if body.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'")
    try:
        from core.feedback import record_feedback
        entry = record_feedback(
            message_id=body.message_id,
            user_input=body.user_input,
            reply=body.reply,
            rating=body.rating,
            intent=body.intent,
            comment=body.comment or "",
            confidence=body.confidence,
        )
        return {"status": "recorded", "rating": body.rating, "ts": entry["ts"]}
    except Exception as e:
        logger.error("feedback error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats")
async def feedback_stats():
    try:
        from core.feedback import get_stats
        return get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/recent")
async def recent_feedback():
    try:
        from core.feedback import get_recent
        return {"feedback": get_recent(20)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
