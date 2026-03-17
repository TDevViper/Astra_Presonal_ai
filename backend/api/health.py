import os
import ollama
from core.smart_guardian import get_full_stats as _smart_stats
from flask import Blueprint, jsonify
from core.proactive import get_welcome_back, analyze_patterns

health_bp   = Blueprint("health", __name__)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@health_bp.route("/health", methods=["GET"])
def health():
    ollama_result = _check_ollama()
    status = {
        "status":  "ok",
        "ollama":  ollama_result,
        "memory":  _check_memory(),
        "vectors": _check_vectors(),
        "brain":   {"status": "ok"},
        "voice":   _check_voice(),
        "redis":   _check_redis(),
        "disk":    _check_disk(),
        "guardian": _check_guardian(),
        "plugins":  _check_plugins(),
        "models":  ollama_result.get("models", []),
    }
    if any(v.get("status") == "error" for v in status.values() if isinstance(v, dict)):
        status["status"] = "degraded"
    try:
        from memory.memory_engine import load_memory as _lm_h
        _mem_h  = _lm_h()
        welcome = get_welcome_back(user_name=_mem_h.get("preferences", {}).get("name", "User"))
        if welcome:
            status["welcome"] = welcome
        patterns = analyze_patterns()
        if patterns.get("top_topics"):
            status["frequent_topics"] = patterns["top_topics"][:3]
    except Exception as _e:
        logger.debug('health check: %s', _e)
    status["brain"]  = status.get("brain",  {}).get("status") == "ok"
    status["memory"] = status.get("memory", {}).get("status") == "ok"
    status["voice"]  = status.get("voice",  {}).get("status") in ("ok", "warning")
    status["ollama"] = status.get("ollama", {}).get("status") == "ok"
    status["redis"]  = status.get("redis",  {}).get("status") == "ok"
    status["disk"]   = status.get("disk",   {}).get("status") in ("ok", "warning")
    return jsonify(status), 200 if status["status"] == "ok" else 207


def _check_ollama() -> dict:
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        models = client.list()
        names  = [m.get("model", m.get("name", "")) for m in models.get("models", [])]
        return {"status": "ok", "models": names}
    except Exception as e:
        return {"status": "error", "error": str(e),
                "hint": "Run `ollama serve` to start Ollama"}


def _check_memory() -> dict:
    try:
        from memory.memory_engine import load_memory
        memory     = load_memory()
        fact_count = len(memory.get("user_facts", []))
        return {"status": "ok", "facts_stored": fact_count}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_voice() -> dict:
    try:
        import importlib.util
        if importlib.util.find_spec("kokoro"):
            return {"status": "ok"}
        tts_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tts_kokoro.py")
        if os.path.exists(tts_path):
            return {"status": "ok"}
        return {"status": "warning", "error": "kokoro not found"}
    except Exception as e:
        return {"status": "warning", "error": str(e)}


def _check_plugins() -> dict:
    try:
        from tools.plugin_watcher import list_plugins
        plugins = list_plugins()
        return {"status": "ok", "loaded": plugins, "count": len(plugins)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_guardian() -> dict:
    try:
        from core.process_guardian import get_state
        state = get_state()
        return {
            "status":   "ok" if state["running"] else "stopped",
            "restarts": state["restarts"],
            "alerts":   state["alerts"][:3],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_redis() -> dict:
    try:
        import redis, os
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            socket_connect_timeout=1, decode_responses=True
        )
        r.ping()
        dbsize = r.dbsize()
        return {"status": "ok", "keys": dbsize}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_disk() -> dict:
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_gb  = round(free  / 1e9, 1)
        total_gb = round(total / 1e9, 1)
        pct_used = round(used / total * 100, 1)
        status   = "ok" if pct_used < 85 else ("warning" if pct_used < 95 else "critical")
        return {"status": status, "free_gb": free_gb, "total_gb": total_gb, "used_pct": pct_used}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_vectors() -> dict:
    try:
        from memory.vector_store import get_collection_size
        count = get_collection_size()
        return {"status": "ok", "vectors_stored": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@health_bp.route("/health/score", methods=["GET"])
def health_score():
    try:
        stats = _smart_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
