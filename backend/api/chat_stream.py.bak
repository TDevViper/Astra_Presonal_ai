import json
from flask import Blueprint, Response, request, stream_with_context
from core.brain_singleton import get_brain

stream_bp = Blueprint("stream", __name__)

@stream_bp.route("/chat/stream", methods=["POST", "OPTIONS"])
def chat_stream():
    if request.method == "OPTIONS":
        return "", 204

    data    = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return Response(
            f"data: {json.dumps({'type': 'done', 'full': '', 'error': 'No message'})}\n\n",
            mimetype="text/event-stream"
        )

    def generate():
        try:
            from knowledge.entity_extractor import extract_and_store
            from memory.memory_engine import load_memory
            _mem = load_memory()
            _name = _mem.get("preferences", {}).get("name", "User")
            extract_and_store(message, user_name=_name, use_llm=False)
        except Exception:
            pass

        result = get_brain().process(message)
        reply  = result.get("reply", "")
        agent  = result.get("agent", "astra")
        intent = result.get("intent", "")

        yield f"data: {json.dumps({'type': 'meta', 'model': agent, 'intent': intent})}\n\n"

        for word in reply.split():
            yield f"data: {json.dumps({'type': 'token', 'text': word + ' '})}\n\n"

        done_payload = {
            "type":             "done",
            "full":             reply,
            "agent":            agent,
            "intent":           intent,
            "emotion":          result.get("emotion", "neutral"),
            "confidence":       result.get("confidence", 0.6),
            "confidence_label": result.get("confidence_label", "MEDIUM"),
            "confidence_emoji": result.get("confidence_emoji", "🟡"),
            "tool_used":        result.get("tool_used", False),
            "memory_updated":   result.get("memory_updated", False),
        }
        yield f"data: {json.dumps(done_payload)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
