import logging
from flask import Blueprint, request, jsonify

logger   = logging.getLogger(__name__)
voice_bp = Blueprint("voice", __name__)
_wake_listener = None


@voice_bp.route("/voice/say", methods=["POST"])
def say():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    try:
        from tts_kokoro import speak_async
        speak_async(text)
        return jsonify({"status": "speaking", "text": text[:100]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/stream", methods=["POST"])
def stream_and_speak():
    data       = request.get_json() or {}
    user_input = data.get("text", "").strip()
    if not user_input:
        return jsonify({"error": "No text provided"}), 400
    try:
        from core.brain_singleton import get_brain
        from tts_kokoro import speak_async
        brain  = get_brain()
        result = brain.process(user_input)
        reply  = result.get("reply", "")
        if reply:
            speak_async(reply)
        return jsonify({"status": "streaming", "reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/listen", methods=["POST"])
def listen():
    data     = request.get_json() or {}
    duration = int(data.get("duration", 5))
    try:
        from voice.voice_engine import listen_once
        text = listen_once(duration=duration)
        return jsonify({"text": text, "duration": duration})
    except Exception as e:
        return jsonify({"error": str(e), "text": ""}), 500


@voice_bp.route("/voice/start", methods=["POST"])
def start_wake():
    global _wake_listener
    try:
        from voice.voice_engine import WakeWordListener
        from core.brain_singleton import get_brain
        from tts_kokoro import speak_async
        brain = get_brain()
        def on_wake(query: str):
            result = brain.process(query)
            reply  = result.get("reply", "")
            if reply:
                speak_async(reply)
        _wake_listener = WakeWordListener(callback=on_wake)
        _wake_listener.start()
        return jsonify({"status": "listening", "wake_word": "hey astra"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/stop", methods=["POST"])
def stop_wake():
    global _wake_listener
    try:
        if _wake_listener:
            _wake_listener.stop()
            _wake_listener = None
    except Exception:
        pass
    return jsonify({"status": "stopped"})
