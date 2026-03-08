import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE     = os.path.join(_BACKEND_DIR, "memory", "data", "response_log.json")


def _classify_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["weather", "temperature", "forecast"]): return "weather"
    if any(w in t for w in ["task", "todo", "remind"]):             return "tasks"
    if any(w in t for w in ["turn on", "turn off", "light"]):       return "device"
    if any(w in t for w in ["search", "find", "what is", "news"]):  return "search"
    if any(w in t for w in ["code", "function", "class", "bug"]):   return "code"
    return "general"


class SelfImprovementEngine:

    def log_response(self, user_input: str, response: str,
                     confidence: float, user_rating: Optional[int] = None):
        entry = {
            "ts":         datetime.now().isoformat(),
            "input":      user_input[:200],
            "response":   response[:400],
            "confidence": confidence,
            "rating":     user_rating,
            "intent":     _classify_intent(user_input)
        }
        logs = self._load()
        logs.append(entry)
        self._save(logs[-1000:])

    def analyze_weak_spots(self) -> Dict[str, float]:
        logs      = self._load()
        by_intent: Dict[str, list] = {}
        for log in logs:
            intent = log.get("intent", "general")
            by_intent.setdefault(intent, []).append(log["confidence"])
        return {
            intent: round(sum(scores) / len(scores), 2)
            for intent, scores in by_intent.items()
        }

    def get_report(self) -> str:
        weak = self.analyze_weak_spots()
        if not weak:
            return "No response data yet."
        lines = ["📊 Self-Improvement Report:"]
        for intent, avg in sorted(weak.items(), key=lambda x: x[1]):
            bar = "🟢" if avg >= 0.85 else "🟡" if avg >= 0.6 else "🔴"
            lines.append(f"  {bar} {intent}: {avg:.0%} avg confidence")
        return "\n".join(lines)

    def _load(self):
        if not os.path.exists(LOG_FILE):
            return []
        try:
            with open(LOG_FILE) as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self, logs):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)


_engine = SelfImprovementEngine()

def log_response(user_input, response, confidence, rating=None):
    _engine.log_response(user_input, response, confidence, rating)

def get_report():
    return _engine.get_report()
