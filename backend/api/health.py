# ==========================================
# api/health.py
# Priority 14: /health endpoint
# ==========================================

from flask import Blueprint, jsonify
from core.proactive import get_welcome_back, analyze_patterns
import ollama

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    status: dict = {
        "status":  "ok",
        "ollama":  _check_ollama(),
        "memory":  _check_memory(),
        "vectors": _check_vectors(),
    }
    # Overall status = degraded if any component is down
    if any(v.get("status") == "error" for v in status.values() if isinstance(v, dict)):
        status["status"] = "degraded"

    # Add welcome back message
    try:
        welcome = get_welcome_back(user_name="Arnav")
        if welcome:
            status["welcome"] = welcome
        patterns = analyze_patterns()
        if patterns.get("top_topics"):
            status["frequent_topics"] = patterns["top_topics"][:3]
    except Exception:
        pass

    return jsonify(status), 200 if status["status"] == "ok" else 207


def _check_ollama() -> dict:
    try:
        models = ollama.list()
        names  = [m["name"] for m in models.get("models", [])]
        return {"status": "ok", "models": names}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_memory() -> dict:
    try:
        from memory.memory_engine import load_memory
        memory    = load_memory()
        fact_count = len(memory.get("user_facts", []))
        return {"status": "ok", "facts_stored": fact_count}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_vectors() -> dict:
    try:
        from memory.vector_store import get_collection_size
        count = get_collection_size()
        return {"status": "ok", "vectors_stored": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}