# ==========================================
# api/stream.py — Streaming responses
# ==========================================

import json
import logging
import ollama
import os
from flask import Blueprint, request, Response, stream_with_context

logger = logging.getLogger(__name__)
stream_bp = Blueprint("stream_api", __name__)


@stream_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """Streaming chat endpoint — word by word response."""
    try:
        from core.brain import brain
        from memory.memory_engine import load_memory
        from core.model_manager import _check_server

        data       = request.get_json()
        user_input = data.get("message", "").strip()

        if not user_input:
            return Response("data: {\"error\": \"No message\"}\n\n",
                            mimetype="text/event-stream")

        memory    = load_memory()
        user_name = memory.get("preferences", {}).get("name", "Arnav")

        # Auto-select server — fast failover
        gpu_url   = "http://100.113.54.3:11434"
        local_url = "http://localhost:11434"
        base_url  = gpu_url if _check_server(gpu_url, timeout=1) else local_url
        os.environ["OLLAMA_HOST"] = base_url
        # Force ollama client to use correct host
        import ollama as _ollama
        _ollama.Client(host=base_url)
        client = _ollama.Client(host=base_url)

        # Get model + context from brain
        query_intent   = brain.model_manager.classify_query_intent(user_input)
        selected_model = brain.model_manager.select_model(user_input, query_intent)

        # Build context
        from memory.semantic_recall import build_semantic_context
        from memory.episodic import build_episodic_context
        from personality.system import build_system_prompt
        from utils.language_detector import detect_language, get_language_instruction
        from emotion.emotion_detector import detect_emotion

        emotion_label, _ = detect_emotion(user_input)
        semantic_ctx, _  = build_semantic_context(user_input, user_name=user_name)
        episodic_ctx     = build_episodic_context(user_input, user_name)
        lang             = detect_language(user_input)
        lang_instr       = get_language_instruction(lang)

        context = build_system_prompt(
            user_name=user_name, memory=memory,
            emotion=emotion_label, intent=query_intent,
            episodic_ctx=episodic_ctx, semantic_ctx=semantic_ctx,
            lang_instruction=lang_instr
        )

        messages = [{"role": "system", "content": context}]
        for h in brain.conversation_history[-6:]:
            messages.append(h)
        messages.append({"role": "user", "content": user_input})

        def generate():
            full_reply = ""
            try:
                # Send metadata first
                meta = json.dumps({
                    "type":   "meta",
                    "model":  selected_model,
                    "intent": query_intent,
                    "server": "GPU" if base_url == gpu_url else "Local"
                })
                yield f"data: {meta}\n\n"

                # Stream tokens
                stream = client.chat(
                    model=selected_model,
                    messages=messages,
                    stream=True,
                    options={"temperature": 0.7, "num_predict": 400, "top_p": 0.9}
                )

                for chunk in stream:
                    token = chunk["message"]["content"]
                    if token:
                        full_reply += token
                        payload = json.dumps({"type": "token", "text": token})
                        yield f"data: {payload}\n\n"

                # Send done signal
                done = json.dumps({"type": "done", "full": full_reply})
                yield f"data: {done}\n\n"

                # Store in history
                brain.conversation_history.append({"role": "user",      "content": user_input})
                brain.conversation_history.append({"role": "assistant",  "content": full_reply})
                if len(brain.conversation_history) > 10:
                    brain.conversation_history = brain.conversation_history[-10:]

                # Store episode
                from memory.episodic import store_episode
                store_episode(user_input, full_reply, intent=query_intent,
                              emotion=emotion_label, user_name=user_name)

            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control":               "no-cache",
                "X-Accel-Buffering":           "no",
                "Access-Control-Allow-Origin": "*",
            }
        )

    except Exception as e:
        logger.error(f"Stream endpoint error: {e}")
        return Response(
            f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n",
            mimetype="text/event-stream"
        )


@stream_bp.route("/chat/stream", methods=["OPTIONS"])
def stream_options():
    return Response(status=200, headers={
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })
