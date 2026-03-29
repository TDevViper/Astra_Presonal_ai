from auth.rbac import require_permission
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()

def _load():
    from memory.memory_engine import load_memory
    return load_memory()

def _save(memory):
    from memory.memory_engine import save_memory
    save_memory(memory)

@router.get("/memory")
async def get_memory():
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _load)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MemoryUpdate(BaseModel):
    user_facts: Optional[List[Any]] = None
    preferences: Optional[Dict[str, Any]] = None

@router.post("/memory")
async def update_memory(body: MemoryUpdate):
    try:
        loop   = asyncio.get_event_loop()
        memory = await loop.run_in_executor(None, _load)
        if body.user_facts is not None:
            memory["user_facts"] = body.user_facts
        if body.preferences is not None:
            memory["preferences"].update(body.preferences)
        await loop.run_in_executor(None, _save, memory)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/memory")
async def clear_memory():
    try:
        loop = asyncio.get_event_loop()
        cur  = await loop.run_in_executor(None, _load)
        name = cur.get("preferences", {}).get("name", "User")
        await loop.run_in_executor(None, _save, {
            "user_facts": [], "preferences": {"name": name},
            "conversation_summary": [], "emotional_patterns": {}
        })
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/facts")
async def get_facts():
    try:
        loop   = asyncio.get_event_loop()
        memory = await loop.run_in_executor(None, _load)
        return {"facts": memory.get("user_facts", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/summary")
async def get_summary():
    try:
        loop   = asyncio.get_event_loop()
        memory = await loop.run_in_executor(None, _load)
        return {"summary": memory.get("conversation_summary", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
