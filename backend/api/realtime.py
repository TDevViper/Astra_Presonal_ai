import os
from core.brain_singleton import get_brain as _get_rt_brain

import logging
from flask import Blueprint, request, jsonify

logger      = logging.getLogger(__name__)
realtime_bp = Blueprint("realtime", __name__)

# Any question while camera is active = use vision
# Don't restrict by keywords — if image is sent, always use llava
VISION_TRIGGERS = [
    "see", "look", "show", "watch", "camera", "finger", "hand",
    "hold", "what is this", "what's this", "what am i", "what do you see",
    "describe", "count", "how many", "read", "what does",
    "can you see", "do you see", "currently", "showing", "this device",
    "this phone", "this object", "tell me about this", "my background",
    "what am i doing", "tell me what", "what i am", "i am holding",
    "i'm holding", "through my camera", "through the camera",
    "can you see me", "see me", "my hand", "my face", "my room"
]

def _wants_vision(text: str) -> bool:
    return any(w in text.lower() for w in VISION_TRIGGERS)


@realtime_bp.route("/realtime/talk", methods=["POST"])
def realtime_talk():
    data     = request.get_json() or {}
    duration = int(data.get("duration", 5))
    image    = data.get("image")

    try:
        from voice.listener import record_audio, transcribe, is_silent
        audio = record_audio(duration=duration)

        if is_silent(audio):
            return jsonify({"text": "", "reply": "", "silent": True})

        user_text = transcribe(audio)
        if not user_text.strip():
            return jsonify({"text": "", "reply": "", "silent": True})

        logger.info(f"🎤 Heard: {user_text}")



        # If image is provided and question is visual — always use vision
        image_b64 = image if (image and _wants_vision(user_text)) else None

        result = _get_rt_brain().process(user_text, vision_mode=bool(image_b64))
        reply  = result.get("reply", "Say that again?")

        logger.info(f"🤖 [{result.get('agent')}] {reply[:80]}")

        from voice.speaker import speak_async
        speak_async(reply)

        return jsonify({
            "text":   user_text,
            "reply":  reply,
            "agent":  result.get("agent", "astra"),
            "intent": result.get("intent", ""),
            "vision": image_b64 is not None,
            "silent": False
        })

    except Exception as e:
        logger.error(f"Realtime talk error: {e}")
        return jsonify({"error": str(e)}), 500


@realtime_bp.route("/realtime/status", methods=["GET"])
def realtime_status():
    import ollama
    GPU_HOST = os.getenv("REMOTE_GPU_HOST", "")
    status   = {}
    try:
        from voice.listener import get_model
        get_model()
        status["whisper"] = "ready"
    except Exception as e:
        status["whisper"] = f"error: {e}"
    try:
        client = ollama.Client(host=GPU_HOST or "http://localhost:11434")
        models = client.list()
        names  = [m.get("model", m.get("name", "")) for m in models.get("models", [])]
        status["gpu"]    = "ready"
        status["models"] = names
        status["llava"]  = any("llava" in n for n in names)
    except Exception as e:
        status["gpu"] = f"error: {e}"
    try:
        import sounddevice as sd
        sd.query_devices()
        status["mic"] = "ready"
    except Exception as e:
        status["mic"] = f"error: {e}"
    return jsonify(status)