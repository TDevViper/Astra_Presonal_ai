import psutil
from flask import Blueprint, jsonify

stats_bp = Blueprint("system_stats", __name__)

@stats_bp.route("/system/stats", methods=["GET"])
def system_stats():
    cpu  = psutil.cpu_percent(interval=0.2)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return jsonify({
        "cpu":    {"percent": cpu},
        "memory": {"percent": ram.percent, "used_gb": round(ram.used/1e9,1), "total_gb": round(ram.total/1e9,1)},
        "disk":   {"percent": disk.percent, "used_gb": round(disk.used/1e9,1), "total_gb": round(disk.total/1e9,1)},
    })

@stats_bp.route("/model", methods=["GET"])
def get_model():
    try:
        import ollama
        client  = ollama.Client(host="http://localhost:11434")
        models  = client.list()
        names   = [m.get("model", m.get("name", "")) for m in models.get("models", [])]
        current = names[0] if names else "phi3:mini"
        # Try to get current from brain
        try:
            from core.brain_singleton import get_brain
            brain = get_brain()
            current = brain.model_manager.current_model
        except Exception:
            pass  # TODO: handle
        return jsonify({"current": current, "available": names})
    except Exception as e:
        return jsonify({"current": "phi3:mini", "available": ["phi3:mini"], "error": str(e)})

@stats_bp.route("/model/set", methods=["POST", "OPTIONS"])
@stats_bp.route("/model", methods=["POST"])
def set_model():
    from flask import request
    data  = request.get_json() or {}
    model = data.get("model", "")
    if not model:
        return jsonify({"error": "no model specified"}), 400
    try:
        from core.brain_singleton import get_brain
        brain = get_brain()
        brain.model_manager.current_model = model
        return jsonify({"status": "ok", "model": model})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
