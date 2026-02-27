import logging
import os
import base64
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

vision_bp = Blueprint("vision", __name__)

# Snapshot directory (defined once globally)
SNAP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "snapshots"
)
os.makedirs(SNAP_DIR, exist_ok=True)


# ───────────────────────────────────────────
# POST /vision/screen
# ───────────────────────────────────────────
@vision_bp.route("/vision/screen", methods=["POST"])
def vision_screen():
    try:
        from vision.vision_engine import vision_engine
        data = request.get_json(silent=True) or {}
        result = vision_engine.analyze_screen(
            user_context=data.get("context", "")
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"/vision/screen error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/camera
# ───────────────────────────────────────────
@vision_bp.route("/vision/camera", methods=["POST"])
def vision_camera():
    try:
        from vision.vision_engine import vision_engine
        data = request.get_json(silent=True) or {}
        result = vision_engine.analyze_camera(
            user_context=data.get("context", "")
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"/vision/camera error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/analyze_b64
# ───────────────────────────────────────────
@vision_bp.route("/vision/analyze_b64", methods=["POST"])
def vision_analyze_b64():
    """
    Accept base64 image directly from browser WebRTC frame.
    Browser sends:
    { image: <base64>, mode: 'camera'|'screen', context: '...' }
    """
    try:
        from vision.analyzer import analyze

        data = request.get_json(silent=True)
        if not data or "image" not in data:
            return jsonify({"error": "No image provided"}), 400

        b64     = data["image"]
        mode    = data.get("mode", "camera")
        context = data.get("context", "")

        result = analyze(b64, mode=mode, user_context=context)

        # Save snapshot for /vision/last
        try:
            image_bytes = base64.b64decode(b64)
            with open(os.path.join(SNAP_DIR, f"last_{mode}.jpg"), "wb") as f:
                f.write(image_bytes)
        except Exception as snap_error:
            logger.warning(f"Snapshot save failed: {snap_error}")

        return jsonify(result)

    except Exception as e:
        logger.error(f"/vision/analyze_b64 error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/analyze (by path)
# ───────────────────────────────────────────
@vision_bp.route("/vision/analyze", methods=["POST"])
def vision_analyze():
    try:
        from vision.vision_engine import vision_engine

        data = request.get_json(silent=True) or {}
        path = data.get("path", "")

        if not path:
            return jsonify({"error": "No path provided"}), 400

        if not os.path.exists(path):
            return jsonify({"error": "File does not exist"}), 404

        result = vision_engine.analyze_image(
            path,
            user_context=data.get("context", "")
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"/vision/analyze error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────
# GET /vision/last/<source>
# ───────────────────────────────────────────
@vision_bp.route("/vision/last/<source>", methods=["GET"])
def vision_last(source):
    try:
        if source not in ("camera", "screen"):
            return jsonify({"error": "Invalid source"}), 400

        path = os.path.join(SNAP_DIR, f"last_{source}.jpg")

        if not os.path.exists(path):
            return jsonify({"error": "No snapshot yet"}), 404

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return jsonify({"image": b64, "source": source})

    except Exception as e:
        logger.error(f"/vision/last error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/watch/start
# ───────────────────────────────────────────
@vision_bp.route("/vision/watch/start", methods=["POST"])
def vision_watch_start():
    try:
        from vision.vision_engine import vision_engine
        data = request.get_json(silent=True) or {}

        interval = int(data.get("interval", 15))
        vision_engine.watch_screen(interval=interval)

        return jsonify({"status": "watching", "interval": interval})

    except Exception as e:
        logger.error(f"/vision/watch/start error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────
# POST /vision/watch/stop
# ───────────────────────────────────────────
@vision_bp.route("/vision/watch/stop", methods=["POST"])
def vision_watch_stop():
    try:
        from vision.vision_engine import vision_engine
        vision_engine.stop_watch()
        return jsonify({"status": "stopped"})
    except Exception as e:
        logger.error(f"/vision/watch/stop error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ───────────────────────────────────────────
# GET /vision/status
# ───────────────────────────────────────────
@vision_bp.route("/vision/status", methods=["GET"])
def vision_status():
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

        return jsonify({
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
                "GET  /vision/status"
            ]
        })

    except Exception as e:
        logger.error(f"/vision/status error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500