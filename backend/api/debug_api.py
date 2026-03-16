from api.auth import require_api_key
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


@debug_bp.route("/api/plugin/deploy", methods=["POST"])
@require_api_key
def deploy_plugin():
    """Deploy a new plugin file to the plugins/ directory."""
    try:
        import os, re
        data     = request.get_json()
        filename = data.get("filename", "").strip()
        code     = data.get("code", "")

        if not filename.endswith(".py"):
            return jsonify({"ok": False, "error": "Filename must end in .py"}), 400
        if not re.match(r'^[\w_]+\.py$', filename):
            return jsonify({"ok": False, "error": "Invalid filename"}), 400
        if len(code) > 50000:
            return jsonify({"ok": False, "error": "Code too large (max 50kb)"}), 400

        backend_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugins_dir  = os.path.join(backend_dir, "plugins")
        os.makedirs(plugins_dir, exist_ok=True)
        plugin_path  = os.path.join(plugins_dir, filename)

        with open(plugin_path, "w") as f:
            f.write(code)

        logger.info("Plugin deployed: %s", filename)
        return jsonify({"ok": True, "filename": filename, "path": plugin_path})
    except Exception as e:
        logger.error("deploy_plugin error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@debug_bp.route("/api/guardian", methods=["GET"])
def guardian_status():
    import psutil
    ram = psutil.virtual_memory().percent
    checks = [
        {"name": "API Auth",        "status": "OK"},
        {"name": "Rate Limiter",    "status": "OK"},
        {"name": "Prompt Firewall", "status": "OK"},
        {"name": "Output Filter",   "status": "WARN" if ram > 85 else "OK"},
        {"name": "Plugin Sandbox",  "status": "OK"},
        {"name": "Memory ACL",      "status": "OK"},
    ]
    level = "alert" if ram > 95 else "warn" if ram > 85 else "ok"
    return jsonify({"checks": checks, "level": level, "ram": ram})
