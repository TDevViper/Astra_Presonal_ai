# ==========================================
# api/chat_stream.py — SSE streaming endpoint
# ==========================================

import json
import logging
from flask import Blueprint, request, Response, stream_with_context

logger    = logging.getLogger(__name__)
stream_bp = Blueprint("stream", __name__)


@stream_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """
    Server-Sent Events endpoint.
    Frontend connects and receives tokens as they arrive.
    Also triggers Kokoro TTS sentence by sentence in parallel.
    """
    data       = request.get_json()
    user_input = (data or {}).get("message", "").strip()

    if not user_input:
        return Response("data: {\"error\": \"No message\"}\n\n",
                        mimetype="text/event-stream")

    def generate():
        try:
            from core.brain import brain
            for chunk in brain.process_stream(user_input):
                token = chunk.get("token", "")
                if token:
                    payload = json.dumps({"token": token}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
            yield "data: {\"done\": true}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {{\"error\": \"{e}\"}}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
