import logging
import os
import base64
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

vision_bp = APIRouter()

# Snapshot directory (defined once globally)
from config import config as _cfg

SNAP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "snapshots"
)
os.makedirs(SNAP_DIR, exist_ok=True)


# ───────────────────────────────────────────
# POST /vision/screen
# ───────────────────────────────────────────
@vision_bp.post("/vision/screen")
def vision_screen(request: Request):
    try:
        from vision.vision_engine import vision_engine

        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        result = vision_engine.analyze_screen(user_context=data.get("context", ""))
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"/vision/screen error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/camera
# ───────────────────────────────────────────
@vision_bp.post("/vision/camera")
def vision_camera(request: Request):
    try:
        from vision.vision_engine import vision_engine

        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        result = vision_engine.analyze_camera(user_context=data.get("context", ""))
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"/vision/camera error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/analyze_b64
# ───────────────────────────────────────────
@vision_bp.post("/vision/analyze_b64")
def vision_analyze_b64(request: Request):
    """
    Accept base64 image directly from browser WebRTC frame.
    Browser sends:
    { image: <base64>, mode: 'camera'|'screen', context: '...' }
    """
    try:
        from vision.analyzer import analyze

        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else None)
        if not data or "image" not in data:
            return JSONResponse(content={"error": "No image provided"}, status_code=400)

        b64 = data["image"]
        mode = data.get("mode", "camera")
        context = data.get("context", "")

        result = analyze(b64, mode=mode, user_context=context)

        # Save snapshot for /vision/last
        try:
            image_bytes = base64.b64decode(b64)
            with open(os.path.join(SNAP_DIR, f"last_{mode}.jpg"), "wb") as f:
                f.write(image_bytes)
        except Exception as snap_error:
            logger.warning(f"Snapshot save failed: {snap_error}")

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"/vision/analyze_b64 error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/analyze (by path)
# ───────────────────────────────────────────
@vision_bp.post("/vision/analyze")
def vision_analyze(request: Request):
    try:
        from vision.vision_engine import vision_engine

        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        path = data.get("path", "")

        if not path:
            return JSONResponse(content={"error": "No path provided"}, status_code=400)

        if not os.path.exists(path):
            return JSONResponse(content={"error": "File does not exist"}, status_code=404)

        result = vision_engine.analyze_image(path, user_context=data.get("context", ""))

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"/vision/analyze error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500


# ───────────────────────────────────────────
# GET /vision/last/<source>
# ───────────────────────────────────────────
@vision_bp.get("/vision/last/<source>")
def vision_last(source):
    try:
        if source not in ("camera", "screen"):
            return JSONResponse(content={"error": "Invalid source"}, status_code=400)

        path = os.path.join(SNAP_DIR, f"last_{source}.jpg")

        if not os.path.exists(path):
            return JSONResponse(content={"error": "No snapshot yet"}, status_code=404)

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return JSONResponse(content={"image": b64, "source": source})

    except Exception as e:
        logger.error(f"/vision/last error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/watch/start
# ───────────────────────────────────────────
@vision_bp.post("/vision/watch/start")
def vision_watch_start(request: Request):
    try:
        from vision.vision_engine import vision_engine

        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})

        interval = int(data.get("interval", 15))
        vision_engine.watch_screen(interval=interval)

        return JSONResponse(content={"status": "watching", "interval": interval})

    except Exception as e:
        logger.error(f"/vision/watch/start error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/watch/stop
# ───────────────────────────────────────────
@vision_bp.post("/vision/watch/stop")
def vision_watch_stop(request: Request):
    try:
        from vision.vision_engine import vision_engine

        vision_engine.stop_watch()
        return JSONResponse(content={"status": "stopped"})
    except Exception as e:
        logger.error(f"/vision/watch/stop error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500


# ───────────────────────────────────────────
# GET /vision/status
# ───────────────────────────────────────────
@vision_bp.get("/vision/status")
def vision_status(request: Request):
    try:
        import ollama

        raw = ollama.list()
        models = []

        if hasattr(raw, "models"):
            models = [
                m.model
                for m in raw.models
                if hasattr(m, "model") and isinstance(m.model, str)
            ]

        return JSONResponse(content=
            {
                "llava_ready": any("llava" in model.lower() for model in models),
                "models": models,
                "endpoints": [
                    "POST /vision/screen",
                    "POST /vision/camera",
                    "POST /vision/analyze_b64",
                    "POST /vision/analyze",
                    "GET  /vision/last/<source>",
                    "POST /vision/watch/start",
                    "POST /vision/watch/stop",
                    "GET  /vision/status",
                ],
            }
        )

    except Exception as e:
        logger.error(f"/vision/status error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}), 500