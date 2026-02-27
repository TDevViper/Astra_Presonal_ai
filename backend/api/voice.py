import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

voice_bp = Blueprint("voice", __name__)


@voice_bp.route("/voice/status", methods=["GET"])
def voice_status():
    """Get voice engine status."""
    from voice.voice_engine import voice_engine
    return jsonify(voice_engine.get_status())


@voice_bp.route("/voice/start", methods=["POST"])
def voice_start():
    """Start voice mode."""
    try:
        from voice.voice_engine import voice_engine
        data = request.get_json() or {}
        mode = data.get("mode", "wake_word")  # wake_word | push_to_talk

        if mode == "wake_word":
            voice_engine.start_wake_word_mode()
            return jsonify({"status": "started", "mode": "wake_word"})

        elif mode == "push_to_talk":
            duration = data.get("duration", 5)
            voice_engine.start_push_to_talk(duration=duration)
            return jsonify({"status": "listening", "mode": "push_to_talk", "duration": duration})

        return jsonify({"error": "Invalid mode. Use 'wake_word' or 'push_to_talk'"}), 400

    except Exception as e:
        logger.error(f"❌ Voice start error: {e}")
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/stop", methods=["POST"])
def voice_stop():
    """Stop voice engine."""
    try:
        from voice.voice_engine import voice_engine
        voice_engine.stop()
        return jsonify({"status": "stopped"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/say", methods=["POST"])
def voice_say():
    """Make ASTRA speak a specific text."""
    try:
        data = request.get_json()
        text = data.get("text", "")
        if not text:
            return jsonify({"error": "No text provided"}), 400

        from voice.speaker import speak_async
        speak_async(text)
        return jsonify({"status": "speaking", "text": text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_bp.route("/voice/listen", methods=["POST"])
def voice_listen():
    """Record audio and return transcription."""
    try:
        data = request.get_json() or {}
        duration = data.get("duration", 5)

        from voice.listener import listen
        text = listen(duration=duration)

        return jsonify({"status": "transcribed", "text": text})

    except Exception as e:
        logger.error(f"❌ Listen error: {e}")
        return jsonify({"error": str(e)}), 500