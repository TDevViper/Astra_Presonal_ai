import json
from flask import Blueprint, Response, request, stream_with_context
from core.orchestrator import orchestrator

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
        result = orchestrator.run(message)
        reply  = result.get("reply", "")
        agent  = result.get("agent", "astra")
        intent = result.get("intent", "")

        yield f"data: {json.dumps({'type': 'meta', 'model': agent, 'intent': intent})}\n\n"

        words = reply.split()
        for word in words:
            yield f"data: {json.dumps({'type': 'token', 'text': word + ' '})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'full': reply, 'agent': agent, 'intent': intent, 'emotion': result.get('emotion', 'neutral'), 'confidence': result.get('confidence', 0.9), 'confidence_label': 'HIGH', 'confidence_emoji': '🟢', 'tool_used': False, 'memory_updated': False})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
