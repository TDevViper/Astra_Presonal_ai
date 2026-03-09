import json, os
from datetime import datetime
from typing import Dict

LOG_FILE = "backend/memory/data/response_log.json"

def classify_intent(text: str) -> str:
    text = text.lower()
    if any(w in text for w in ["turn on", "turn off", "light", "lock"]):  return "smart_home"
    if any(w in text for w in ["weather", "news", "search"]):             return "search"
    if any(w in text for w in ["code", "python", "debug", "error"]):      return "coding"
    if any(w in text for w in ["remember", "memory", "recall"]):          return "memory"
    if any(w in text for w in ["camera", "screen", "see"]):               return "vision"
    return "general"

class SelfImprovementEngine:
    def __init__(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def log_response(self, user_input: str, response: str,
                     confidence: float, user_rating: int = None):
        entry = {
            "ts":         datetime.now().isoformat(),
            "input":      user_input[:200],
            "response":   response[:400],
            "confidence": confidence,
            "rating":     user_rating,
            "intent":     classify_intent(user_input)
        }
        logs = self._load()
        logs.append(entry)
        with open(LOG_FILE, "w") as f:
            json.dump(logs[-1000:], f, indent=2)

    def analyze_weak_spots(self) -> Dict:
        logs      = self._load()
        by_intent = {}
        for log in logs:
            intent = log.get("intent", "general")
            by_intent.setdefault(intent, []).append(log["confidence"])
        return {
            intent: round(sum(scores) / len(scores), 2)
            for intent, scores in by_intent.items()
        }

    def generate_report(self) -> str:
        spots = self.analyze_weak_spots()
        if not spots:
            return "No response data yet."
        lines = ["📊 Astra Self-Improvement Report", ""]
        for intent, avg in sorted(spots.items(), key=lambda x: x[1]):
            bar = "🔴" if avg < 0.6 else ("🟡" if avg < 0.8 else "🟢")
            lines.append(f"{bar} {intent}: avg confidence {avg}")
        return "\n".join(lines)

    def auto_refine_prompts(self):
        import ollama
        weak   = {k: v for k, v in self.analyze_weak_spots().items() if v < 0.7}
        client = ollama.Client()
        for intent, avg_conf in weak.items():
            examples = self._get_weak_examples(intent)
            prompt   = (
                f"These '{intent}' responses had low confidence ({avg_conf}).\n"
                f"Suggest a better system prompt for this intent type.\n"
                f"Examples: {examples}\nReturn: improved system prompt only."
            )
            response = client.chat(model="mistral",
                                   messages=[{"role": "user", "content": prompt}])
            with open(f"backend/memory/data/refined_prompt_{intent}.txt", "w") as f:
                f.write(response["message"]["content"])

    def _get_weak_examples(self, intent: str, limit=5):
        return [l for l in self._load()
                if l.get("intent") == intent and l["confidence"] < 0.7][-limit:]

    def _load(self):
        if not os.path.exists(LOG_FILE):
            return []
        try:
            with open(LOG_FILE) as f:
                return json.load(f)
        except Exception:
            return []
