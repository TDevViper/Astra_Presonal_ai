import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/memory")
async def get_memory():
    try:
        from memory.memory_engine import load_memory
        return load_memory()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MemoryUpdate(BaseModel):
    user_facts: Optional[List[Any]] = None
    preferences: Optional[Dict[str, Any]] = None

@router.post("/memory")
async def update_memory(body: MemoryUpdate):
    try:
        from memory.memory_engine import load_memory, save_memory
        memory = load_memory()
        if body.user_facts is not None:
            memory["user_facts"] = body.user_facts
        if body.preferences is not None:
            memory["preferences"].update(body.preferences)
        save_memory(memory)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/memory")
async def clear_memory():
    try:
        from memory.memory_engine import load_memory, save_memory
        cur = load_memory()
        name = cur.get("preferences", {}).get("name", "User")
        save_memory({"user_facts": [], "preferences": {"name": name},
                     "conversation_summary": [], "emotional_patterns": {}})
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/facts")
async def get_facts():
    try:
        from memory.memory_engine import load_memory
        return {"facts": load_memory().get("user_facts", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/summary")
async def get_summary():
    try:
        from memory.memory_engine import load_memory
        return {"summary": load_memory().get("conversation_summary", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
