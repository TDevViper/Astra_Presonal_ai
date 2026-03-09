import logging
import ollama
import requests
from typing import Dict

logger = logging.getLogger(__name__)

GPU_HOST   = "http://100.113.54.3:11434"
LOCAL_HOST = "http://localhost:11434"


def _get_client():
    try:
        r = requests.get(GPU_HOST, timeout=1)
        if r.status_code == 200:
            return ollama.Client(host=GPU_HOST), "mistral:latest"
    except Exception:
        pass
    return ollama.Client(host=LOCAL_HOST), "phi3:mini"


def critic_review(
    reply: str,
    user_name: str,
    memory: Dict,
    user_input: str = "",
    model: str = None
) -> str:
    if not reply or len(reply.strip()) < 10:
        return reply

    try:
        client, selected_model = _get_client()
        if model:
            selected_model = model

        prompt = f"""You are a strict reply reviewer for an AI assistant named ASTRA.

Original question: {user_input}
Draft reply: {reply}

Rules:
- If reply is good → return it EXACTLY as-is, no changes
- If reply is off-topic or wrong → fix it in 1-2 sentences
- If reply mentions wrong names or hallucinations → correct them
- NEVER add preamble like "Here is the improved reply:"
- Output ONLY the final reply text, nothing else

Final reply:"""

        response = client.chat(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 150},
        )
        result = response["message"]["content"].strip()

        if not result or len(result) < 5:
            return reply

        return result

    except Exception as e:
        logger.warning(f"LLM critic failed ({e}), using original")
        return reply
