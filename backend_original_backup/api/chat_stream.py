# ==========================================
# api/chat_stream.py — SSE streaming v3
# ==========================================

import json
import logging
from flask import Blueprint, request, Response, stream_with_context

logger    = logging.getLogger(__name__)
stream_bp = Blueprint("stream", __name__)


@stream_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """
    Emits:
      {"type":"meta",  "model":str, "intent":str}
      {"type":"token", "text":str}
      {"type":"done",  "full":str, "agent":str, "intent":str,
                       "emotion":str, "confidence":float,
                       "tool_used":bool, "memory_updated":bool, "mode":str}
    """
    data       = request.get_json()
    user_input = (data or {}).get("message", "").strip()

    if not user_input:
        return Response(
            'data: {"type":"token","text":"No message received"}\n\n'
            'data: {"type":"done","full":"","confidence":0}\n\n',
            mimetype="text/event-stream"
        )

    def generate():
        try:
            from core.brain_singleton import get_brain
            brain = get_brain()

            query_intent   = brain.model_manager.classify_query_intent(user_input)
            selected_model = brain.model_manager.select_model(user_input, query_intent)

            yield f"data: {json.dumps({'type':'meta','model':selected_model,'intent':query_intent})}\n\n"

            meta_payload = None

            for chunk in get_brain().process_stream(user_input):
                if "meta" in chunk:
                    meta_payload = chunk["meta"]
                    continue
                token = chunk.get("token", "")
                if token:
                    yield f"data: {json.dumps({'type':'token','text':token}, ensure_ascii=False)}\n\n"

            try:
                from personality.modes import get_current_mode
                active_mode = get_current_mode()
            except Exception:
                active_mode = "jarvis"

            if meta_payload:
                done = {
                    "type":           "done",
                    "full":           meta_payload.get("full", ""),
                    "agent":          meta_payload.get("agent", selected_model),
                    "intent":         meta_payload.get("intent", query_intent),
                    "emotion":        meta_payload.get("emotion", "neutral"),
                    "confidence":     meta_payload.get("confidence", 0.75),
                    "tool_used":      meta_payload.get("tool_used", False),
                    "memory_updated": meta_payload.get("memory_updated", True),
                    "mode":           active_mode,
                }
            else:
                try:
                    from emotion.emotion_detector import detect_emotion
                    emotion, _ = detect_emotion(user_input)
                except Exception:
                    emotion = "neutral"
                try:
                    from core.confidence import score as conf_score
                    confidence = conf_score(query_intent, query_intent)
                except Exception:
                    confidence = 0.75
                done = {
                    "type":           "done",
                    "full":           "",
                    "agent":          selected_model,
                    "intent":         query_intent,
                    "emotion":        emotion,
                    "confidence":     confidence,
                    "tool_used":      False,
                    "memory_updated": False,
                    "mode":           active_mode,
                }

            yield f"data: {json.dumps(done)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type':'token','text':f'Error: {e}'})}\n\n"
            yield 'data: {"type":"done","full":"","confidence":0}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
