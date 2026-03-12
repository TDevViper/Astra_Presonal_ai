import logging
from flask import Blueprint, request, jsonify
from personality.modes import list_modes, set_mode, get_current_mode, get_mode_banner, get_mode_config

logger  = logging.getLogger(__name__)
mode_bp = Blueprint("mode_api", __name__)


@mode_bp.route("/mode/list", methods=["GET"])
def list_all_modes():
    try:
        return jsonify({"modes": list_modes(), "current": get_current_mode()})
    except Exception as e:
        logger.error("mode list error: %s", e)
        return jsonify({"error": str(e)}), 500


@mode_bp.route("/mode/set", methods=["POST"])
def switch_mode():
    try:
        data = request.get_json() or {}
        mode = data.get("mode", "").strip().lower()
        if not mode:
            return jsonify({"error": "No mode specified"}), 400
        if set_mode(mode):
            return jsonify({
                "status": "ok",
                "mode":   get_current_mode(),
                "banner": get_mode_banner(),
                "config": get_mode_config()
            })
        return jsonify({"error": f"Unknown mode: {mode}"}), 400
    except Exception as e:
        logger.error("mode set error: %s", e)
        return jsonify({"error": str(e)}), 500


@mode_bp.route("/mode/current", methods=["GET"])
def current_mode():
    try:
        return jsonify({
            "mode":   get_current_mode(),
            "banner": get_mode_banner(),
            "config": get_mode_config()
        })
    except Exception as e:
        logger.error("mode current error: %s", e)
        return jsonify({"error": str(e)}), 500
