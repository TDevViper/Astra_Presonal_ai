import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from personality.modes import (
    list_modes,
    set_mode,
    get_current_mode,
    get_mode_banner,
    get_mode_config,
)

logger = logging.getLogger(__name__)
mode_bp = APIRouter()

_MODE_ALIASES = {
    "casual": "chill",
    "relaxed": "chill",
    "chill": "chill",
    "focus": "focus",
    "focused": "focus",
    "work": "focus",
    "jarvis": "jarvis",
    "default": "jarvis",
    "normal": "jarvis",
    "expert": "expert",
    "phd": "expert",
    "advanced": "expert",
    "debug": "debug",
    "engineer": "debug",
}


@mode_bp.get("/mode/list")
def list_all_modes():
    try:
        return JSONResponse(content={"modes": list_modes(), "current": get_current_mode()})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@mode_bp.post("/mode/set")
def switch_mode():
    try:
        data = request.get_json() or {}
        raw = data.get("mode", "").strip().lower()
        if not raw:
            return JSONResponse(content={"error": "No mode specified"}, status_code=400)
        mode = _MODE_ALIASES.get(raw, raw)
        if set_mode(mode):
            return JSONResponse(content=
                {
                    "status": "ok",
                    "mode": get_current_mode(),
                    "banner": get_mode_banner(),
                    "config": get_mode_config(),
                }
            )
        return JSONResponse(content=
            {
                "error": f"Unknown mode: '{raw}'",
                "valid_modes": sorted(_MODE_ALIASES.keys()),
            }
        ), 400
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@mode_bp.get("/mode/current")
def current_mode():
    try:
        return JSONResponse(content=
            {
                "mode": get_current_mode(),
                "banner": get_mode_banner(),
                "config": get_mode_config(),
            }
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500
