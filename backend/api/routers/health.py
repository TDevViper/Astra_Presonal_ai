from auth.rbac import require_permission, require_permission
from fastapi import Depends
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health():
    """Public liveness check only."""
    return {"status": "ok", "version": "5.1"}

@router.get("/health/detailed")
async def health_detailed(current_user=Depends(require_permission("system_stats"))):
    from api.health import (
        _check_ollama,
        _check_memory,
        _check_vectors,
        _check_voice,
        _check_redis,
        _check_disk,
        _check_guardian,
        _check_plugins,
    )

    ollama_result = _check_ollama()
    status = {
        "status": "ok",
        "ollama": ollama_result,
        "memory": _check_memory(),
        "vectors": _check_vectors(),
        "brain": {"status": "ok"},
        "voice": _check_voice(),
        "redis": _check_redis(),
        "disk": _check_disk(),
        "guardian": _check_guardian(),
        "plugins": _check_plugins(),
        "models": ollama_result.get("models", []),
    }
    if any(v.get("status") == "error" for v in status.values() if isinstance(v, dict)):
        status["status"] = "degraded"
    try:
        from memory.memory_engine import load_memory
        from core.proactive import get_welcome_back, analyze_patterns

        mem = load_memory()
        welcome = get_welcome_back(
            user_name=mem.get("preferences", {}).get("name", "User")
        )
        if welcome:
            status["welcome"] = welcome
        patterns = analyze_patterns()
        if patterns.get("top_topics"):
            status["frequent_topics"] = patterns["top_topics"][:3]
    except Exception:
        pass
    status["brain"] = status.get("brain", {}).get("status") == "ok"
    status["memory"] = status.get("memory", {}).get("status") == "ok"
    status["voice"] = status.get("voice", {}).get("status") in ("ok", "warning")
    status["ollama"] = status.get("ollama", {}).get("status") == "ok"
    status["redis"] = status.get("redis", {}).get("status") == "ok"
    status["disk"] = status.get("disk", {}).get("status") in ("ok", "warning")
    return JSONResponse(status, status_code=200 if status["status"] == "ok" else 207)


@router.get("/health/score")
async def health_score(current_user=Depends(require_permission("system_stats"))):
    try:
        from core.smart_guardian import get_full_stats, get_trend_summary

        stats = get_full_stats()
        stats["trend"] = get_trend_summary()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
