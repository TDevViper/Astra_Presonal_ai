import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

def _ollama_models():
    try:
        import requests as _req
        base = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        resp = _req.get(f"{base}/api/tags", timeout=5)
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []

def _current_model():
    try:
        from core.brain_singleton import get_brain
        return get_brain().model_manager.current_model
    except Exception:
        return "phi3:mini"

@router.get("/model")
async def model_status():
    return {"available": _ollama_models(), "current": _current_model()}

@router.get("/model/info")
async def model_info():
    try:
        from core.brain_singleton import get_brain
        return get_brain().get_model_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SwitchRequest(BaseModel):
    model: str

@router.post("/model/switch")
@router.post("/model/set")
async def switch_model(body: SwitchRequest):
    try:
        from core.brain_singleton import get_brain
        brain = get_brain()
        if not brain.model_manager.force_set(body.model):
            raise HTTPException(status_code=400, detail=f"Model '{body.model}' not available")
        return {"status": "switched", "model": body.model}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model/available")
@router.get("/model/list")
async def available_models():
    return {"models": _ollama_models()}
