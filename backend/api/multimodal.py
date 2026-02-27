import logging
import subprocess
import os
import base64
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

multimodal_bp = Blueprint("multimodal", __name__)


@multimodal_bp.route("/talk", methods=["POST"])
def talk():
    try:
        data  = request.get_json() or {}
        image = data.get("image")
        text  = data.get("text", "").strip()
        speak = data.get("speak", True)

        # ── Step 1: Analyze image if provided ────────────────
        visual_context = ""
        if image:
            from vision.analyzer import analyze
            vision_result  = analyze(image, mode="camera", user_context=text)
            summary        = vision_result.get("summary", "")
            objects        = vision_result.get("objects_detected", [])
            jarvis         = vision_result.get("jarvis_response", "")
            visual_context = jarvis or summary

        # ── Step 2: Build prompt cleanly ──────────────────────
        # Key insight: visual_context is ASTRA's own observation.
        # Combine it naturally so brain doesn't leak it back.
        if visual_context and text:
            prompt = f"{text}"  # just send the user's question
        elif visual_context:
            # No question — just describe what's seen naturally
            prompt = f"hello"
        elif text:
            prompt = f"Arnav says: '{text}'. Reply conversationally in 1-2 sentences max."
        else:
            return jsonify({"error": "No input provided"}), 400

        # ── Step 3: Get reply from brain ──────────────────────
        from core.brain import brain
        result = brain.process(prompt, vision_mode=True)
        reply  = result.get("reply", "").strip()
        words = reply.split()
        if len(words) > 40:
            reply = " ".join(words[:40]) + "."
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
        for marker in ["[You can see", "[ASTRA sees", "You are a real-time", "(Vision:"]:
            if marker in reply:
                reply = reply[:reply.index(marker)].strip()

        if not reply:
            reply = "I'm here. What do you need?"

        # ── Step 5: Speak ─────────────────────────────────────
        if speak and reply:
            clean = reply.replace('"', '').replace("'", "")[:300]
            subprocess.Popen(
                ["say", "-v", "Samantha", "-r", "185", clean],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        return jsonify({
            "reply":          reply,
            "visual_context": visual_context,
            "agent":          result.get("agent"),
            "emotion":        result.get("emotion"),
            "confidence":     result.get("confidence"),
        })

    except Exception as e:
        logger.error(f"❌ Talk error: {e}")
        return jsonify({"error": str(e)}), 500


@multimodal_bp.route("/talk/listen", methods=["POST"])
def talk_listen():
    try:
        data     = request.get_json() or {}
        duration = data.get("duration", 5)
        from voice.listener import listen
        text = listen(duration=duration)
        return jsonify({"text": text, "heard": bool(text.strip())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500