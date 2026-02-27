# ==========================================
# vision/analyzer.py
# LLaVA-powered structured vision analysis
# ==========================================

import logging
import json
import re
from typing import Dict, Optional

import ollama

logger = logging.getLogger(__name__)

VISION_MODEL = "llava:7b"

# ── System Prompts ────────────────────────────────────────────

SCREEN_PROMPT = """You are ASTRA Screen Intelligence — a visual reasoning engine analyzing a live screen capture.

Priorities:
1. Identify the active application and what the user is doing.
2. Extract visible code, errors, terminal output, or UI states.
3. Detect workflow patterns and potential issues.
4. Suggest concrete next actions.

If code is visible:
- Identify language and filename if shown
- Identify bug patterns or issues
- Suggest exact fix

If terminal is visible:
- Parse the error stack
- Identify root cause
- Suggest the exact command or fix

If a diagram or whiteboard is visible:
- Convert it to structured representation
- Identify architectural patterns

Respond in this exact JSON format:
{
  "summary": "one sentence of what you see",
  "app_detected": "name of app or null",
  "content_type": "code|terminal|browser|diagram|text|mixed|other",
  "extracted": {
    "language": "python/js/etc or null",
    "filename": "if visible or null",
    "error": "exact error message if any or null",
    "key_text": "most important text visible"
  },
  "issues": ["list of problems detected"],
  "suggestions": ["list of concrete actionable suggestions"],
  "jarvis_response": "confident 1-3 sentence JARVIS-style insight"
}"""

CAMERA_PROMPT = """You are ASTRA Vision — the environmental awareness layer of an advanced personal AI.

You are analyzing a live camera feed of the user's physical environment.

Tasks:
1. Identify objects, their positions, and spatial relationships.
2. Detect any text, whiteboards, notebooks, or screens visible.
3. Infer what the user is working on or planning.
4. Identify anything notable, unusual, or actionable.

Speak directly TO Arnav using "you", not "the person".
Be concise and JARVIS-like. Max 2 sentences for jarvis_response.
CRITICAL: Only describe clearly visible objects. No hallucinations.
If blurry, say so. Never invent whiteboards, text, or objects.

Respond in this exact JSON format:
{
  "summary": "one sentence describing the scene",
  "environment": "desk|room|whiteboard|outdoor|other",
  "objects_detected": ["list of key objects"],
  "text_found": "any text visible or null",
  "user_activity": "what the user appears to be doing",
  "whiteboard_content": "structured content if whiteboard visible or null",
  "suggestions": ["actionable suggestions based on what you see"],
  "jarvis_response": "confident 1-3 sentence JARVIS-style observation"
}"""

IMAGE_PROMPT = """You are ASTRA Vision — a reasoning engine with eyes.

Analyze this image deeply. Do NOT just describe it — interpret it.

Extract:
- Objects and their relationships
- Any text or code present
- Diagrams or architectural patterns
- Errors or issues if visible
- What the user likely needs help with

Respond in this exact JSON format:
{
  "summary": "one sentence of what this is",
  "content_type": "code|diagram|photo|screenshot|document|other",
  "objects": ["key objects or elements"],
  "text_extracted": "any text found or null",
  "code_found": "code if present or null",
  "interpretation": "what this means in context",
  "suggestions": ["concrete suggestions"],
  "jarvis_response": "confident 1-3 sentence JARVIS-style insight"
}"""


# ── Core Analyzer ─────────────────────────────────────────────

def analyze(image_b64: str, mode: str = "image", user_context: str = "") -> Dict:
    """
    Analyze image with LLaVA.
    mode: screen | camera | image
    """
    prompts = {
        "screen": SCREEN_PROMPT,
        "camera": CAMERA_PROMPT,
        "image":  IMAGE_PROMPT
    }
    system = prompts.get(mode, IMAGE_PROMPT)

    user_msg = "Analyze this."
    if user_context:
        user_msg = f"Context: {user_context}\n\nAnalyze this."

    try:
        logger.info(f"🔍 Analyzing image (mode={mode})...")

        response = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg, "images": [image_b64]}
            ],
            options={"temperature": 0.2, "num_predict": 800}
        )

        raw = response["message"]["content"]
        logger.info(f"✅ Analysis complete")

        # Parse JSON from response
        result = _parse_json(raw)
        result["mode"] = mode
        result["raw"] = raw
        return result

    except Exception as e:
        logger.error(f"❌ Vision analysis error: {e}")
        return {
            "error": str(e),
            "mode": mode,
            "jarvis_response": "Vision system error. Check if llava:7b is running in Ollama.",
            "summary": "Analysis failed"
        }


def _parse_json(text: str) -> Dict:
    """Extract JSON from LLaVA response."""
    # Strip markdown fences
    text = text.strip().strip("```json").strip("```").strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try extracting JSON block
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # Fallback — return raw as jarvis_response
    return {
        "summary": "Analysis complete",
        "jarvis_response": text.strip()[:500],
        "suggestions": []
    }


def analyze_code_in_image(image_b64: str) -> Dict:
    """Specialized code analysis from screenshot."""
    result = analyze(image_b64, mode="screen")

    code = result.get("extracted", {}).get("key_text") or result.get("code_found", "")
    error = result.get("extracted", {}).get("error")

    if error:
        # Ask for specific fix
        try:
            fix_response = ollama.chat(
                model="phi3:mini",
                messages=[{"role": "user", "content": f"Fix this error:\n{error}"}],
                options={"temperature": 0.1, "num_predict": 300}
            )
            result["fix_suggestion"] = fix_response["message"]["content"]
        except Exception:
            pass

    return result