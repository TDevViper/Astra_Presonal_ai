import logging
from flask import Blueprint, request, jsonify

logger     = logging.getLogger(__name__)
execute_bp = Blueprint("execute", __name__)

@execute_bp.route("/capabilities", methods=["GET"])
def get_capabilities():
    try:
        from core.brain_singleton import get_brain
        return jsonify(get_brain().capabilities.get_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@execute_bp.route("/capabilities/<capability>", methods=["PUT"])
def toggle_capability(capability: str):
    try:
        from core.brain_singleton import get_brain
        brain   = get_brain()
        data    = request.get_json() or {}
        enabled = data.get("enabled", False)
        success = brain.capabilities.enable(capability) if enabled else brain.capabilities.disable(capability)
        if success:
            return jsonify({"capability": capability, "enabled": enabled, "status": "updated"})
        return jsonify({"error": f"Unknown capability: {capability}", "valid": list(brain.capabilities.all_flags().keys())}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@execute_bp.route("/execute", methods=["POST"])
def execute_tool():
    try:
        data      = request.get_json() or {}
        tool_name = data.get("tool")
        params    = data.get("params", {})
        approved  = data.get("approved", False)

        # Shortcut: {"code": "print(1+1)"} runs python directly
        if not tool_name and "code" in data:
            tool_name = "python_sandbox"
            params    = {"code": data["code"]}
            approved  = True

        if not tool_name:
            return jsonify({"error": "No tool specified",
                            "hint": '{"tool":"python_sandbox","params":{"code":"print(1+1)"},"approved":true}'}), 400

        DANGEROUS = {"python_sandbox", "git_tool", "file_reader"}
        if tool_name in DANGEROUS and not approved:
            return jsonify({"status":"approval_required","tool":tool_name,"message":"Send with 'approved':true"}), 202

        from tools.tool_router import ToolRouter
        result = ToolRouter().execute(tool_name, params)
        return jsonify({"status": "success", "tool": tool_name, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
