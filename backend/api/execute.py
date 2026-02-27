import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

execute_bp = Blueprint("execute", __name__)


@execute_bp.route("/capabilities", methods=["GET"])
def get_capabilities():
    """Get current system capabilities."""
    from core.brain import brain
    return jsonify(brain.capabilities.get_status())


@execute_bp.route("/capabilities/<capability>", methods=["PUT"])
def toggle_capability(capability: str):
    """Enable or disable a capability."""
    try:
        from core.brain import brain
        data = request.get_json()
        enabled = data.get("enabled", False)

        if enabled:
            success = brain.capabilities.enable(capability)
        else:
            success = brain.capabilities.disable(capability)

        if success:
            logger.info(f"⚙️  Capability '{capability}' set to {enabled}")
            return jsonify({
                "capability": capability,
                "enabled": enabled,
                "status": "updated"
            })

        return jsonify({"error": f"Unknown capability: {capability}"}), 404

    except Exception as e:
        logger.error(f"❌ Error toggling capability: {e}")
        return jsonify({"error": str(e)}), 500


@execute_bp.route("/execute", methods=["POST"])
def execute_tool():
    """Execute a tool with approval check."""
    try:
        from core.brain import brain
        data = request.get_json()

        tool_name = data.get("tool")
        params = data.get("params", {})
        approved = data.get("approved", False)

        if not tool_name:
            return jsonify({"error": "No tool specified"}), 400

        # Tools that require explicit approval
        DANGEROUS_TOOLS = {"python_sandbox", "git_tool", "file_reader"}

        if tool_name in DANGEROUS_TOOLS and not approved:
            return jsonify({
                "status": "approval_required",
                "tool": tool_name,
                "params": params,
                "message": f"Tool '{tool_name}' requires explicit approval. Send again with approved: true"
            }), 202

        # Execute via tool router
        from tools.tool_router import ToolRouter
        router = ToolRouter()
        result = router.execute(tool_name, params)

        logger.info(f"🔧 Tool executed: {tool_name}")
        return jsonify({
            "status": "success",
            "tool": tool_name,
            "result": result
        })

    except Exception as e:
        logger.error(f"❌ Tool execution error: {e}")
        return jsonify({"error": str(e)}), 500