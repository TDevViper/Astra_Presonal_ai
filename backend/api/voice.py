import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
voice_bp = APIRouter()
_wake_listener = None


@voice_bp.post("/voice/say")
def say(request: Request):
    data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
    text = data.get("text", "").strip()
    if not text:
        return JSONResponse(content={"error": "No text provided"}, status_code=400)
    try:
        from tts_kokoro import speak_async

        speak_async(text)
        return JSONResponse(content={"status": "speaking", "text": text[:100]})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@voice_bp.post("/voice/stream")
def stream_and_speak(request: Request):
    data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
    user_input = data.get("text", "").strip()
    if not user_input:
        return JSONResponse(content={"error": "No text provided"}, status_code=400)
    try:
        from core.brain_singleton import get_brain
        from tts_kokoro import speak_async

        brain = get_brain()
        result = brain.process(user_input)
        reply = result.get("reply", "")
        if reply:
            speak_async(reply)
        return JSONResponse(content={"status": "streaming", "reply": reply})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@voice_bp.post("/voice/listen")
def listen(request: Request):
    data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
    duration = int(data.get("duration", 5))
    try:
        from voice.voice_engine import listen_once

        text = listen_once(duration=duration)
        return JSONResponse(content={"text": text, "duration": duration})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "text": ""}), 500


@voice_bp.post("/voice/start")
def start_wake(request: Request):
    global _wake_listener
    try:
        from voice.voice_engine import WakeWordListener
        from core.brain_singleton import get_brain
        from tts_kokoro import speak_async

        brain = get_brain()

        def on_wake(query: str):
            result = brain.process(query)
            reply = result.get("reply", "")
            if reply:
                speak_async(reply)

        _wake_listener = WakeWordListener(callback=on_wake)
        _wake_listener.start()
        return JSONResponse(content={"status": "listening", "wake_word": "hey astra"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500


@voice_bp.post("/voice/stop")
def stop_wake(request: Request):
    global _wake_listener
    try:
        if _wake_listener:
            _wake_listener.stop()
            _wake_listener = None
    except Exception as _e:
        logger.debug("voice api: %s", _e)
    return JSONResponse(content={"status": "stopped"})