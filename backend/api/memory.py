import logging
from flask import Blueprint, request, jsonify

logger    = logging.getLogger(__name__)
memory_bp = Blueprint("memory", __name__)


@memory_bp.route("/memory", methods=["GET"])
def get_memory():
    """Get current memory."""
    try:
        from memory.memory_engine import load_memory
        return jsonify(load_memory())
    except Exception as e:
        logger.error("get_memory error: %s", e)
        return jsonify({"error": str(e)}), 500


@memory_bp.route("/memory", methods=["POST"])
def update_memory():
    """Manually update memory."""
    try:
        from memory.memory_engine import load_memory, save_memory
        data   = request.get_json()
        memory = load_memory()
        if "user_facts" in data:
            memory["user_facts"] = data["user_facts"]
        if "preferences" in data:
            memory["preferences"].update(data["preferences"])
        save_memory(memory)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error("update_memory error: %s", e)
        return jsonify({"error": str(e)}), 500


@memory_bp.route("/memory", methods=["DELETE"])
def clear_memory():
    """Clear all memory."""
    try:
        from memory.memory_engine import load_memory, save_memory
        cur           = load_memory()
        existing_name = cur.get("preferences", {}).get("name", "User")
        save_memory({
            "user_facts": [],
            "preferences": {"name": existing_name},
            "conversation_summary": [],
            "emotional_patterns": {}
        })
        logger.info("Memory cleared")
        return jsonify({"status": "cleared"})
    except Exception as e:
        logger.error("clear_memory error: %s", e)
        return jsonify({"error": str(e)}), 500


@memory_bp.route("/memory/facts", methods=["GET"])
def get_facts():
    """Get only user facts."""
    try:
        from memory.memory_engine import load_memory
        memory = load_memory()
        return jsonify({"facts": memory.get("user_facts", [])})
    except Exception as e:
        logger.error("get_facts error: %s", e)
        return jsonify({"error": str(e)}), 500


@memory_bp.route("/memory/summary", methods=["GET"])
def get_summary():
    """Get conversation summary."""
    try:
        from memory.memory_engine import load_memory
        memory = load_memory()
        return jsonify({"summary": memory.get("conversation_summary", [])})
    except Exception as e:
        logger.error("get_summary error: %s", e)
        return jsonify({"error": str(e)}), 500


from flask import Blueprint as _B2
_style_bp = Blueprint("style_api", __name__) if False else None

# Attach to existing memory_bp
from flask import request as _req

@memory_bp.route("/api/style", methods=["GET"])
def get_style():
    try:
        from core.adaptive_personality import _load_style, get_style_addon
        style = _load_style()
        return jsonify({"style": style, "addon": get_style_addon()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@memory_bp.route("/api/style", methods=["POST"])
def set_style():
    try:
        data = _req.get_json()
        from core.adaptive_personality import update_style_manually
        key, value = data.get("key"), data.get("value")
        if update_style_manually(key, value):
            return jsonify({"ok": True, "key": key, "value": value})
        return jsonify({"error": f"Invalid key/value: {key}={value}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@memory_bp.route("/api/style/refine", methods=["POST"])
def force_refine():
    try:
        from core.adaptive_personality import maybe_refine
        result = maybe_refine(force=True)
        return jsonify({"refined": result is not None, "addon": result or ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


from flask import Blueprint as _B2
_style_bp = Blueprint("style_api", __name__) if False else None

# Attach to existing memory_bp
from flask import request as _req

