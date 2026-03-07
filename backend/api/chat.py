import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        from core.brain import brain
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        user_input = data.get("message", "")

        if not user_input:
            return jsonify({"error": "No message provided"}), 400

        logger.info(f"💬 User: {user_input[:50]}...")
        result = brain.process(user_input)
        logger.info(f"🤖 ASTRA: {result['reply'][:50]}...")

        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500
