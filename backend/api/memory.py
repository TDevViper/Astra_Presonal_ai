import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
memory_bp = APIRouter()


@memory_bp.get("/memory")
def get_memory(request: Request):
    """Get current memory."""
    try:
        from memory.memory_engine import load_memory

        return JSONResponse(content=load_memory())
    except Exception as e:
        logger.error("get_memory error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@memory_bp.post("/memory")
def update_memory(request: Request):
    """Manually update memory."""
    try:
        from memory.memory_engine import load_memory, save_memory

        data = await request.json()
        memory = load_memory()
        if "user_facts" in data:
            memory["user_facts"] = data["user_facts"]
        if "preferences" in data:
            memory["preferences"].update(data["preferences"])
        save_memory(memory)
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        logger.error("update_memory error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@memory_bp.delete("/memory")
def clear_memory(request: Request):
    """Clear all memory."""
    try:
        from memory.memory_engine import load_memory, save_memory

        cur = load_memory()
        existing_name = cur.get("preferences", {}).get("name", "User")
        save_memory(
            {
                "user_facts": [],
                "preferences": {"name": existing_name},
                "conversation_summary": [],
                "emotional_patterns": {},
            }
        )
        logger.info("Memory cleared")
        return JSONResponse(content={"status": "cleared"})
    except Exception as e:
        logger.error("clear_memory error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@memory_bp.get("/memory/facts")
def get_facts(request: Request):
    """Get only user facts."""
    try:
        from memory.memory_engine import load_memory

        memory = load_memory()
        return JSONResponse(content={"facts": memory.get("user_facts", [])})
    except Exception as e:
        logger.error("get_facts error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@memory_bp.get("/memory/summary")
def get_summary(request: Request):
    """Get conversation summary."""
    try:
        from memory.memory_engine import load_memory

        memory = load_memory()
        return JSONResponse(content={"summary": memory.get("conversation_summary", [])})
    except Exception as e:
        logger.error("get_summary error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500



_style_bp = APIRouter() if False else None

# Attach to existing memory_bp


@memory_bp.get("/api/style")
def get_style(request: Request):
    try:
        from core.adaptive_personality import _load_style, get_style_addon

        style = _load_style()
        return JSONResponse(content={"style": style, "addon": get_style_addon()})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@memory_bp.post("/api/style")
def set_style(request: Request):
    try:
        data = _req.get_json()
        from core.adaptive_personality import update_style_manually

        key, value = data.get("key"), data.get("value")
        if update_style_manually(key, value):
            return JSONResponse(content={"ok": True, "key": key, "value": value})
        return JSONResponse(content={"error": f"Invalid key/value: {key}={value}"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@memory_bp.post("/api/style/refine")
def force_refine(request: Request):
    try:
        from core.adaptive_personality import maybe_refine

        result = maybe_refine(force=True)
        return JSONResponse(content={"refined": result is not None, "addon": result or ""})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500



_style_bp = APIRouter() if False else None

# Attach to existing memory_bp