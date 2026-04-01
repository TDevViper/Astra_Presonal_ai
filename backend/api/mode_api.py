import logging
from flask import Blueprint, request, jsonify
from personality.modes import (
    list_modes,
    set_mode,
    get_current_mode,
    get_mode_banner,
    get_mode_config,
)

logger = logging.getLogger(__name__)
mode_bp = Blueprint("mode_api", __name__)

_MODE_ALIASES = {
    "casual": "chill",
    "relaxed": "chill",
    "chill": "chill",
    "focus": "focus",
    "focused": "focus",
    "work": "focus",
    "jarvis": "jarvis",
    "default": "jarvis",
    "normal": "jarvis",
    "expert": "expert",
    "phd": "expert",
    "advanced": "expert",
    "debug": "debug",
    "engineer": "debug",
}


@mode_bp.route("/mode/list", methods=["GET"])
def list_all_modes():
    try:
        return jsonify({"modes": list_modes(), "current": get_current_mode()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mode_bp.route("/mode/set", methods=["POST"])
def switch_mode():
    try:
        data = request.get_json() or {}
        raw = data.get("mode", "").strip().lower()
        if not raw:
            return jsonify({"error": "No mode specified"}), 400
        mode = _MODE_ALIASES.get(raw, raw)
        if set_mode(mode):
            return jsonify(
                {
                    "status": "ok",
                    "mode": get_current_mode(),
                    "banner": get_mode_banner(),
                    "config": get_mode_config(),
                }
            )
        return jsonify(
            {
                "error": f"Unknown mode: '{raw}'",
                "valid_modes": sorted(_MODE_ALIASES.keys()),
            }
        ), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mode_bp.route("/mode/current", methods=["GET"])
def current_mode():
    try:
        return jsonify(
            {
                "mode": get_current_mode(),
                "banner": get_mode_banner(),
                "config": get_mode_config(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
