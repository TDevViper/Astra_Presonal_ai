import logging
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
model_bp = APIRouter()


def _ollama_models(request: Request):
    try:
        import requests as _req

        base = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        resp = _req.get(f"{base}/api/tags", timeout=5)
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def _current_model(request: Request):
    try:
        from core.brain_singleton import get_brain

        return get_brain().model_manager.current_model
    except Exception:
        return "phi3:mini"


@model_bp.get("/model")
def model_status(request: Request):
    try:
        return JSONResponse(content={"available": _ollama_models(), "current": _current_model()})
    except Exception as e:
        logger.error("model status error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@model_bp.get("/model/info")
def model_info(request: Request):
    try:
        from core.brain_singleton import get_brain

        return JSONResponse(content=get_brain().get_model_info())
    except Exception as e:
        logger.error("model info error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@model_bp.post("/model/switch")
def force_switch_model(request: Request):
    try:
        from core.brain_singleton import get_brain

        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        model = data.get("model")
        if not model:
            return JSONResponse(content={"error": "No model specified"}, status_code=400)
        brain = get_brain()
        success = brain.model_manager.force_set(model)
        if success:
            logger.info("Model switched to: %s", model)
            return JSONResponse(content={"status": "switched", "model": model})
        return JSONResponse(content={"error": f"Model '{model}' not available"}, status_code=400)
    except Exception as e:
        logger.error("model switch error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@model_bp.post("/model/set")
def set_model(request: Request):
    try:
        return force_switch_model()
    except Exception as e:
        logger.error("model set error: %s", e)
        return JSONResponse(content={"error": str(e)}), 500


@model_bp.get("/model/available")
def available_models(request: Request):
    try:
        return JSONResponse(content={"models": _ollama_models()})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@model_bp.get("/model/list")
def list_models(request: Request):
    try:
        return JSONResponse(content={"models": _ollama_models()})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500