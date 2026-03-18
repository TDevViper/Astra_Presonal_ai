import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/traces")
async def get_traces():
    from core.observability import get_store
    return {
        "traces": get_store().get_recent(20),
        "stats":  get_store().get_stats(),
    }

@router.get("/api/events")
async def get_events():
    from core.event_bus import get_history, get_stats
    return {
        "events": get_history(30),
        "stats":  get_stats(),
    }

@router.get("/api/self-improve")
async def self_improve_report():
    try:
        from core.self_improve import generate_report, analyze_weak_spots
        return {
            "report":      generate_report(),
            "weak_spots":  analyze_weak_spots(),
        }
    except Exception as e:
        raise
