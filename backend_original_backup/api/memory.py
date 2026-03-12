import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

memory_bp = Blueprint("memory", __name__)


@memory_bp.route("/memory", methods=["GET"])
def get_memory():
    """Get current memory."""
    from memory.memory_engine import load_memory
    memory = load_memory()
    return jsonify(memory)


@memory_bp.route("/memory", methods=["POST"])
def update_memory():
    """Manually update memory."""
    try:
        from memory.memory_engine import load_memory, save_memory
        data = request.get_json()
        memory = load_memory()

        if "user_facts" in data:
            memory["user_facts"] = data["user_facts"]
        if "preferences" in data:
            memory["preferences"].update(data["preferences"])

        save_memory(memory)
        return jsonify({"status": "success"})

    except Exception as e:
        logger.error(f"❌ Error updating memory: {e}")
        return jsonify({"error": str(e)}), 500


@memory_bp.route("/memory", methods=["DELETE"])
def clear_memory():
    """Clear all memory."""
    try:
        from memory.memory_engine import save_memory
        save_memory({
            "user_facts": [],
            "preferences": {"name": "Arnav"},
            "conversation_summary": [],
            "emotional_patterns": {}
        })
        logger.info("🧹 Memory cleared")
        return jsonify({"status": "cleared"})

    except Exception as e:
        logger.error(f"❌ Error clearing memory: {e}")
        return jsonify({"error": str(e)}), 500


@memory_bp.route("/memory/facts", methods=["GET"])
def get_facts():
    """Get only user facts."""
    from memory.memory_engine import load_memory
    memory = load_memory()
    return jsonify({"facts": memory.get("user_facts", [])})


@memory_bp.route("/memory/summary", methods=["GET"])
def get_summary():
    """Get conversation summary."""
    from memory.memory_engine import load_memory
    memory = load_memory()
    return jsonify({"summary": memory.get("conversation_summary", [])})