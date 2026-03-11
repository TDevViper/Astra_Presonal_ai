import logging, os
from flask import Blueprint, request, jsonify

logger   = logging.getLogger(__name__)
model_bp = Blueprint("model", __name__)


def _ollama_models():
    try:
        import requests as _req
        base  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        resp  = _req.get(f"{base}/api/tags", timeout=5)
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def _current_model():
    try:
        from core.brain_singleton import get_brain
        return get_brain().model_manager.current_model
    except Exception:
        return "phi3:mini"


@model_bp.route("/model", methods=["GET"])
def model_status():
    return jsonify({"available": _ollama_models(), "current": _current_model()})


@model_bp.route("/model/info", methods=["GET"])
def model_info():
    try:
        from core.brain_singleton import get_brain
        return jsonify(get_brain().get_model_info())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@model_bp.route("/model/switch", methods=["POST"])
def force_switch_model():
    try:
        from core.brain_singleton import get_brain
        data  = request.get_json() or {}
        model = data.get("model")
        if not model:
            return jsonify({"error": "No model specified"}), 400
        brain   = get_brain()
        success = brain.model_manager.force_set(model)
        if success:
            logger.info(f"Model switched to: {model}")
            return jsonify({"status": "switched", "model": model})
        return jsonify({"error": f"Model '{model}' not available"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@model_bp.route("/model/set", methods=["POST"])
def set_model():
    return force_switch_model()


@model_bp.route("/model/available", methods=["GET"])
def available_models():
    return jsonify({"models": _ollama_models()})


@model_bp.route("/model/list", methods=["GET"])
def list_models():
    return jsonify({"models": _ollama_models()})
