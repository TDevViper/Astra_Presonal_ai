import logging
import subprocess
import os
import base64
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

multimodal_bp = APIRouter()


@multimodal_bp.post("/talk")
def talk(request: Request):
    try:
        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        image = data.get("image")
        text = data.get("text", "").strip()
        speak = data.get("speak", True)

        # ── Step 1: Analyze image if provided ────────────────
        visual_context = ""
        if image:
            from vision.analyzer import analyze

            vision_result = analyze(image, mode="camera", user_context=text)
            summary = vision_result.get("summary", "")
            vision_result.get("objects_detected", [])
            jarvis = vision_result.get("jarvis_response", "")
            visual_context = jarvis or summary

        from memory.memory_engine import load_memory

        user_name = load_memory().get("preferences", {}).get("name", "User")

        # ── Step 2: Build prompt cleanly ──────────────────────
        # Key insight: visual_context is ASTRA's own observation.
        # Combine it naturally so brain doesn't leak it back.
        if visual_context and text:
            prompt = f"{text}"  # just send the user's question
        elif visual_context:
            # No question — just describe what's seen naturally
            prompt = "hello"
        elif text:
            prompt = f"{user_name} says: '{text}'. Reply conversationally in 1-2 sentences max."
        else:
            return JSONResponse(content={"error": "No input provided"}, status_code=400)

        # ── Step 3: Get reply from brain ──────────────────────
        from core.brain_singleton import get_brain

        _brain = get_brain()
        result = _brain.process(prompt, vision_mode=True)
        reply = result.get("reply", "").strip()
        # Cap at 40 words for conversational feel
        words = reply.split()
        if len(words) > 40:
            reply = " ".join(words[:40]) + "."

        # If vision context exists and reply is generic, prepend vision observation
        if visual_context and reply and len(visual_context) > 20:
            # Only prepend if the reply doesn't already address what's seen
            vision_short = visual_context[:120].split(".")[0]
            if text and len(text) > 3:
                pass  # user asked a question, brain answered it — don't override
            else:
                reply = f"{vision_short}. {reply}"

        # ── Step 4: Clean reply ───────────────────────────────
        # Remove any leaked internal context
        for marker in [
            "[You can see",
            "[ASTRA sees",
            "You are a real-time",
            "(Vision:",
        ]:
            if marker in reply:
                reply = reply[: reply.index(marker)].strip()

        if not reply:
            reply = "I'm here. What do you need?"

        # ── Step 5: Speak ─────────────────────────────────────
        if speak and reply:
            clean = reply.replace('"', "").replace("'", "")[:300]
            try:
                from voice.speaker import speak_async

                speak_async(clean)
            except Exception:
                import platform

                if platform.system() == "Darwin":
                    subprocess.Popen(
                        ["say", "-v", "Samantha", "-r", "185", clean],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

        return JSONResponse(content=
            {
                "reply": reply,
                "visual_context": visual_context,
                "agent": result.get("agent"),
                "emotion": result.get("emotion"),
                "confidence": result.get("confidence"),
            }
        )

    except Exception as e:
        logger.error(f"❌ Talk error: {e}")
        return JSONResponse(content={"error": str(e)}), 500


@multimodal_bp.post("/talk/listen")
def talk_listen(request: Request):
    try:
        data = (await request.json() if request.headers.get('content-type','').startswith('application/json') else {})
        duration = data.get("duration", 5)
        from voice.listener import listen

        text = listen(duration=duration)
        return JSONResponse(content={"text": text, "heard": bool(text.strip())})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}), 500