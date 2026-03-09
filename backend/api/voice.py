# ==========================================
# api/voice.py — JARVIS Voice API
# ==========================================

import logging
from flask import Blueprint, request, jsonify

logger    = logging.getLogger(__name__)
voice_bp  = Blueprint("voice", __name__)


@voice_bp.route("/voice/say", methods=["POST"])
def say():
    """Speak text aloud — streaming sentence by sentence."""
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text"}), 400
    try:
        from tts_kokoro import speak_async
        speak_async(text)
        return jsonify({"status": "speaking", "text": text[:100]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/stream", methods=["POST"])
def stream_and_speak():
    """Generate + speak simultaneously — sub-200ms first word."""
    data       = request.get_json()
    user_input = data.get("text", "").strip()
    if not user_input:
        return jsonify({"error": "No text"}), 400
    try:
        from core.brain import stream_response
        from tts_kokoro import speak_streaming
        from personality.system import build_system_prompt
        from memory.memory_engine import load_memory

        memory        = load_memory()
        system_prompt = build_system_prompt(memory)
        generator     = stream_response(user_input, system_prompt)

        import threading
        threading.Thread(
            target=speak_streaming,
            args=(generator,),
            daemon=True
        ).start()

        return jsonify({"status": "streaming"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/listen", methods=["POST"])
def listen():
    """Record audio and return transcription."""
    data     = request.get_json() or {}
    duration = int(data.get("duration", 5))
    try:
        from voice.voice_engine import listen_once
        text = listen_once(duration=duration)
        return jsonify({"text": text, "duration": duration})
    except Exception as e:
        logger.error(f"Listen error: {e}")
        return jsonify({"error": str(e), "text": ""}), 500


@voice_bp.route("/voice/start", methods=["POST"])
def start_wake():
    """Start wake word listener with streaming TTS response."""
    try:
        from voice.voice_engine import WakeWordListener
        from core.brain import Brain, stream_response
        from tts_kokoro import speak_streaming
        from personality.system import build_system_prompt
        from memory.memory_engine import load_memory

        _brain = Brain()

        def on_wake(query: str):
            # First get intent/tools via brain
            result = _brain.process(query)
            reply  = result.get("reply", "")
            if reply:
                # Stream through Kokoro sentence by sentence
                def _gen():
                    words = reply.split()
                    chunk = ""
                    for w in words:
                        chunk += w + " "
                        if len(chunk) > 40:
                            yield chunk
                            chunk = ""
                    if chunk:
                        yield chunk
                speak_streaming(_gen())

        global _wake_listener
        _wake_listener = WakeWordListener(callback=on_wake)
        _wake_listener.start()

        return jsonify({"status": "listening", "wake_word": "hey astra"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/stop", methods=["POST"])
def stop_wake():
    try:
        global _wake_listener
        if _wake_listener:
            _wake_listener.stop()
        return jsonify({"status": "stopped"})
    except Exception:
        return jsonify({"status": "stopped"})


_wake_listener = None
