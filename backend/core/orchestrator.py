import logging
import os
import ollama
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)

GPU_HOST   = "http://100.113.54.3:11434"
LOCAL_HOST = "http://localhost:11434"

# Models actually on GPU
GPU_MODELS   = ["mistral:latest", "llava:7b"]
LOCAL_MODELS = ["phi3:mini", "llama3.2:3b", "mistral:latest"]

TOOL_INTENTS = {
    "whatsapp":   ["whatsapp", "send message to", "send whatsapp"],
    "web_search": ["search for", "google", "look up", "latest news",
                   "current price", "weather in", "who won"],
    "calendar":   ["add to calendar", "schedule", "my schedule", "remind me at"],
    "system":     ["volume up", "volume down", "open app", "close app",
                   "take screenshot", "lock screen"],
    "git":        ["git status", "git log", "git commit", "git diff"],
    "tasks":      ["add task", "my tasks", "show tasks", "complete task"],
    "files":      ["read file", "open file", "show file"],
}

CHAT_INTENTS = {
    "greeting": ["hello", "hi", "hey", "good morning", "good night",
                 "namaste", "kaise ho", "how are you"],
    "identity": ["your name", "who are you", "what are you",
                 "tum kaun", "aap kaun"],
    "creator":  ["who made you", "who built you", "kisne banaya"],
    "farewell": ["bye", "goodbye", "see you", "cya"],
}

SHORTCUT_RESPONSES = {
    "greeting": "Hey! What's up?",
    "identity": "I'm ASTRA, your personal AI assistant built by Arnav.",
    "creator":  "Arnav built me. Pretty cool right?",
    "farewell": "Bye! See you soon.",
}


def _gpu_alive() -> bool:
    try:
        r = requests.get(GPU_HOST, timeout=1)
        return r.status_code == 200
    except Exception:
        return False


def _get_client_and_model(prefer_heavy: bool = False):
    """
    Returns (client, model_name, hw_label).
    Uses GPU mistral for heavy tasks if GPU alive,
    falls back to best available local model.
    """
    if _gpu_alive():
        model = "mistral:latest" if prefer_heavy else "mistral:latest"
        return ollama.Client(host=GPU_HOST), model, "GPU"

    # GPU offline — use local models
    local_client = ollama.Client(host=LOCAL_HOST)
    try:
        result = local_client.list()
        names  = [m.get("model", m.get("name", "")) for m in result.get("models", [])]
        for m in ["llama3.2:3b", "mistral:latest", "phi3:mini"]:
            if any(m in n for n in names):
                return local_client, m, "CPU"
    except Exception:
        pass
    # Last resort
    return local_client, "phi3:mini", "CPU"


def _detect_intent(text: str):
    t = text.lower().strip()
    for tool, triggers in TOOL_INTENTS.items():
        if any(tr in t for tr in triggers):
            return ("tool", tool)
    for intent, triggers in CHAT_INTENTS.items():
        if any(tr in t for tr in triggers):
            return ("chat", intent)
    return ("llm", "general")


class Orchestrator:

    def __init__(self):
        logger.info("🎯 Orchestrator initialized")

    def run(self, user_input: str, image_b64: Optional[str] = None) -> Dict:
        try:
            category, subcategory = _detect_intent(user_input)
            logger.info(f"🎯 Intent: {category}/{subcategory}")

            # Shortcuts — no LLM needed
            if category == "chat":
                reply = SHORTCUT_RESPONSES.get(subcategory, "Hey! What can I do for you?")
                return self._reply(reply, subcategory, "shortcut")

            # Tool routing
            if category == "tool":
                result = self._run_tool(subcategory, user_input)
                if result:
                    return self._reply(result, subcategory, subcategory)
                # Tool returned nothing — fall through to LLM

            # Vision
            if image_b64:
                return self._vision_reply(user_input, image_b64)

            # LLM
            return self._llm_reply(user_input)

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return self._reply(f"Error: {e}", "error", "error")

    def _run_tool(self, tool: str, text: str) -> Optional[str]:
        try:
            if tool == "whatsapp":
                from tools.whatsapp_tool import handle_whatsapp_command
                return handle_whatsapp_command(text)
            if tool == "web_search":
                from tools.web_search import handle_search_command
                return handle_search_command(text)
            if tool == "calendar":
                from tools.calendar_tool import handle_calendar_command
                return handle_calendar_command(text)
            if tool == "system":
                from tools.system_controller import handle_system_command
                return handle_system_command(text)
            if tool == "git":
                from tools.git_tool import git_status
                return git_status().get("output", "No git info")
            if tool == "tasks":
                from tools.task_manager import TaskManager
                return str(TaskManager().list_tasks())
            if tool == "files":
                from tools.file_reader import extract_filepath, read_file
                path = extract_filepath(text)
                return read_file(path) if path else None
        except Exception as e:
            logger.error(f"Tool {tool} error: {e}")
        return None

    def _vision_reply(self, text: str, image_b64: str) -> Dict:
        gpu_up = _gpu_alive()
        client = ollama.Client(host=GPU_HOST if gpu_up else LOCAL_HOST)
        hw     = "GPU" if gpu_up else "CPU"
        logger.info(f"👁️ llava:7b on {hw}")
        response = client.chat(
            model="llava:7b",
            messages=[{
                "role":    "user",
                "content": (
                    "You are Astra, a personal AI with a live camera. "
                    "Answer ONLY what the question asks. Do not describe the full scene. "
                    "If asked about fingers — count them carefully and say the number. "
                    "If asked about hands — describe the hand gesture only. "
                    "Keep answer to 1 sentence max. "
                    f"Question: {text}"
                ),
                "images": [image_b64]
            }],
            options={"temperature": 0.1, "num_predict": 80}
        )
        reply = response["message"]["content"].strip()
        return self._reply(reply, "vision", f"llava:7b ({hw})")

    def _llm_reply(self, text: str) -> Dict:
        client, model, hw = _get_client_and_model(prefer_heavy=True)
        logger.info(f"💬 {model} on {hw}")
        response = client.chat(
            model=model,
            messages=[
                {
                    "role":    "system",
                    "content": (
                        "You are Astra, a smart personal AI assistant. "
                        "Answer in 1-2 sentences max. Be accurate and direct. "
                        "Never make up facts. If unsure, say so briefly."
                    )
                },
                {"role": "user", "content": text}
            ],
            options={"temperature": 0.5, "num_predict": 120}
        )
        reply = response["message"]["content"].strip()
        return self._reply(reply, "general", f"{model} ({hw})")

    def _reply(self, reply: str, intent: str, agent: str) -> Dict:
        return {
            "reply":      reply or "Say that again?",
            "intent":     intent,
            "agent":      agent,
            "confidence": 0.9,
            "emotion":    "neutral",
        }


orchestrator = Orchestrator()
