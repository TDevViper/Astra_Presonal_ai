# ==========================================
# api/voice.py — JARVIS Voice API
# ==========================================

import logging
from flask import Blueprint, request, jsonify

logger    = logging.getLogger(__name__)
voice_bp  = Blueprint("voice", __name__)


@voice_bp.route("/voice/say", methods=["POST"])
def say():
    """Speak text aloud."""
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text"}), 400
    try:
        from voice.voice_engine import speak
        speak(text)
        return jsonify({"status": "speaking", "text": text[:100]})
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
    """Start wake word listener."""
    try:
        from voice.voice_engine import WakeWordListener
        from core.brain import brain

        def on_wake(query: str):
            """Process voice query through brain."""
            result = brain.process(query)
            reply  = result.get("reply", "")
            if reply:
                from voice.voice_engine import speak
                speak(reply)

        global _wake_listener
        _wake_listener = WakeWordListener(callback=on_wake)
        _wake_listener.start()

        return jsonify({"status": "listening", "wake_word": "hey astra"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/stop", methods=["POST"])
def stop_wake():
    """Stop wake word listener."""
    try:
        global _wake_listener
        if _wake_listener:
            _wake_listener.stop()
        return jsonify({"status": "stopped"})
    except Exception:
        return jsonify({"status": "stopped"})


_wake_listener = None
