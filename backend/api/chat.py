import logging
from flask import Blueprint, request, jsonify

logger   = logging.getLogger(__name__)
chat_bp  = Blueprint("chat_api", __name__)

MAX_INPUT_CHARS = 4000


@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data       = request.get_json()
        user_input = data.get("message", "").strip()

        if not user_input or len(user_input) > MAX_INPUT_CHARS:
            return jsonify({"error": f"Message must be 1-{MAX_INPUT_CHARS} characters"}), 400

        logger.info("💬 User: %s", user_input[:50])
        result = get_brain().process(user_input)
        logger.info("🤖 ASTRA: %s", result["reply"][:50])
        return jsonify(result)

    except Exception as e:
        logger.error("chat endpoint error: %s", e)
        return jsonify({"error": str(e)}), 500


def get_brain():
    from core.brain_singleton import get_brain as _get
    return _get()
