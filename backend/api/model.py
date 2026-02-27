import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

model_bp = Blueprint("model", __name__)


@model_bp.route("/model/info", methods=["GET"])
def model_info():
    """Get current model manager status."""
    from core.brain import brain
    return jsonify(brain.get_model_info())


@model_bp.route("/model/switch", methods=["POST"])
def force_switch_model():
    """Force switch to a specific model."""
    try:
        from core.brain import brain
        data = request.get_json()
        model = data.get("model")

        if not model:
            return jsonify({"error": "No model specified"}), 400

        success = brain.model_manager.force_set(model)

        if success:
            logger.info(f"🔀 Model switched to: {model}")
            return jsonify({"status": "switched", "model": model})

        return jsonify({"error": f"Model '{model}' not available"}), 400

    except Exception as e:
        logger.error(f"❌ Error switching model: {e}")
        return jsonify({"error": str(e)}), 500


@model_bp.route("/model/available", methods=["GET"])
def available_models():
    """List all available Ollama models."""
    try:
        import httpx
        from config import config
        response = httpx.get(f"{config.model.base_url}/api/tags")
        models = [m["name"] for m in response.json().get("models", [])]
        return jsonify({"models": models})
    except Exception as e:
        logger.error(f"❌ Error fetching models: {e}")
        return jsonify({"error": str(e)}), 500