from fastapi import APIRouter
from fastapi.responses import JSONResponse
from core.observability import get_store
from core.event_bus import get_history, get_stats

obs_bp = APIRouter()


@obs_bp.get("/api/traces")
def get_traces():
    return JSONResponse(content=
        {
            "traces": get_store().get_recent(20),
            "stats": get_store().get_stats(),
        }
    )


@obs_bp.get("/api/events")
def get_events():
    return JSONResponse(content=
        {
            "events": get_history(30),
            "stats": get_stats(),
        }
    )
