import json
from flask import Blueprint, Response, request, stream_with_context
from core.brain import brain

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
        result = brain.process(message)
        reply  = result.get("reply", "")
        agent  = result.get("agent", "astra")
        intent = result.get("intent", "")

        # Send meta first
        yield f"data: {json.dumps({'type': 'meta', 'model': agent, 'intent': intent})}\n\n"

        # Stream word by word
        words = reply.split()
        for word in words:
            yield f"data: {json.dumps({'type': 'token', 'text': word + ' '})}\n\n"

        # Final done event with full metadata
        yield f"data: {json.dumps({'type': 'done', 'full': reply, 'agent': agent, 'intent': intent, 'emotion': result.get('emotion', 'neutral'), 'confidence': result.get('confidence', 0.8), 'confidence_label': result.get('confidence_label', 'MEDIUM'), 'confidence_emoji': result.get('confidence_emoji', '🟡'), 'tool_used': result.get('tool_used', False), 'memory_updated': result.get('memory_updated', False)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
