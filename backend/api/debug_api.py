# api/debug_api.py
import logging
from flask import Blueprint, request, jsonify

logger    = logging.getLogger(__name__)
debug_bp  = Blueprint("debug_api", __name__)


@debug_bp.route("/api/debug/screen", methods=["POST"])
def debug_screen():
    """Trigger auto-debug on current screen error."""
    try:
        from core.ambient import _live_context
        from core.brain_singleton import get_brain
        brain      = get_brain()
        mem        = brain._mem.load()
        user_name  = brain._mem.user_name(mem)
        error_text = request.get_json(silent=True, force=True).get("error") \
                     or _live_context.get("error_text", "")
        if not error_text:
            # trigger a fresh scan
            from vision.screen_watcher import ScreenWatcher
            sw         = ScreenWatcher()
            error_text = sw.capture_and_analyze(
                "Extract any error message visible on screen. If none, say 'no error'."
            )
        if "no error" in error_text.lower():
            return jsonify({"reply": "No error detected on screen.", "fix_proposed": False})
        from core.auto_debug import run_auto_debug
        result = run_auto_debug(
            error_text, user_name=user_name,
            model=brain.model_manager.select_model(error_text, "technical")
        )
        return jsonify(result)
    except Exception as e:
        logger.error("debug_screen error: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@debug_bp.route("/api/debug/shell", methods=["POST"])
def shell_execute():
    """Execute a shell command with tier-based safety."""
    try:
        data    = request.get_json()
        command = data.get("command", "").strip()
        confirmed      = data.get("confirmed", False)
        sudo_confirmed = data.get("sudo_confirmed", False)
        if not command:
            return jsonify({"error": "No command provided"}), 400
        if data.get("propose_only"):
            from tools.shell_executor import propose_shell
            return jsonify(propose_shell(command))
        from tools.shell_executor import execute_shell
        result = execute_shell(command, confirmed=confirmed,
                               sudo_confirmed=sudo_confirmed)
        return jsonify(result)
    except Exception as e:
        logger.error("shell_execute error: %s", e)
        return jsonify({"error": str(e)}), 500


@debug_bp.route("/api/ambient", methods=["GET"])
def ambient_status():
    """Get current ambient context — what ASTRA sees right now."""
    try:
        from core.ambient import get_live_context
        return jsonify(get_live_context())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
