import json
import os
import logging
import threading
import re
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(_BACKEND, "memory", "data", "response_log.json")
TIPS_FILE = os.path.join(_BACKEND, "memory", "data", "prompt_tips.json")
MAX_LOGS = 500


def classify_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["turn on", "turn off", "light", "lock"]):
        return "smart_home"
    if any(w in t for w in ["weather", "news", "search", "latest"]):
        return "search"
    if any(w in t for w in ["code", "python", "debug", "error", "bug"]):
        return "coding"
    if any(w in t for w in ["remember", "memory", "recall"]):
        return "memory"
    if any(w in t for w in ["camera", "screen", "see", "vision"]):
        return "vision"
    if any(w in t for w in ["why", "how", "explain", "analyze"]):
        return "reasoning"
    return "general"


def _load_logs() -> List[Dict]:
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_logs(logs):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w") as f:
            json.dump(logs[-MAX_LOGS:], f, indent=2)
    except Exception:
        pass


def _load_tips() -> Dict:
    try:
        if os.path.exists(TIPS_FILE):
            with open(TIPS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_tips(tips):
    try:
        os.makedirs(os.path.dirname(TIPS_FILE), exist_ok=True)
        with open(TIPS_FILE, "w") as f:
            json.dump(tips, f, indent=2)
    except Exception:
        pass


def _score_reply(user_input: str, reply: str, intent: str) -> float:
    score = 0.5
    filler_starters = [
        "sure!",
        "certainly!",
        "of course!",
        "great question",
        "absolutely!",
        "i'd be happy",
        "i'm happy to",
    ]
    if any(reply.lower().startswith(f) for f in filler_starters):
        score -= 0.2
    words = len(reply.split())
    if intent in ["reasoning", "coding"] and words < 30:
        score -= 0.15
    if intent == "general" and words > 150:
        score -= 0.1
    if 20 <= words <= 200:
        score += 0.1
    unique_r = len(set(reply.lower().split())) / max(len(reply.split()), 1)
    if unique_r < 0.5:
        score -= 0.15
    if intent == "coding" and "```" in reply:
        score += 0.15
    deflections = ["i don't know", "i'm not sure", "i cannot", "as an ai"]
    if any(d in reply.lower() for d in deflections) and intent == "general":
        score -= 0.1
    return max(0.0, min(1.0, round(score, 2)))


def _deep_score_async(user_input: str, reply: str, entry_ts: str):
    try:
        import ollama

        prompt = f"""Rate this AI reply 0-10. Be strict.
User: {user_input[:200]}
Reply: {reply[:400]}
Output ONLY: {{"score": X, "issue": "one-line issue or empty"}}"""
        resp = ollama.chat(
            model="phi3:mini",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 80},
        )
        raw = resp["message"]["content"].strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            score = float(data.get("score", 5)) / 10.0
            issue = data.get("issue", "")
            logs = _load_logs()
            for entry in logs:
                if entry.get("ts") == entry_ts:
                    entry["llm_score"] = round(score, 2)
                    entry["issue"] = issue
                    break
            _save_logs(logs)
            if score < 0.6 and issue:
                tips = _load_tips()
                intent = classify_intent(user_input)
                tips.setdefault(intent, [])
                if issue not in tips[intent]:
                    tips[intent].append(issue)
                    tips[intent] = tips[intent][-10:]
                _save_tips(tips)
    except Exception:
        pass


_log_counter = 0
_log_counter_lock = threading.Lock()


def log_response(user_input: str, response: str, confidence: float, user_rating=None):
    global _log_counter
    with _log_counter_lock:
        _log_counter += 1
    intent = classify_intent(user_input)
    heuristic = _score_reply(user_input, response, intent)
    ts = datetime.now().isoformat()
    logs = _load_logs()
    logs.append(
        {
            "ts": ts,
            "input": user_input[:200],
            "response": response[:400],
            "confidence": confidence,
            "rating": user_rating,
            "intent": intent,
            "h_score": heuristic,
        }
    )
    _save_logs(logs)
    if heuristic < 0.6 and _log_counter % 10 == 0:
        threading.Thread(
            target=_deep_score_async, args=(user_input, response, ts), daemon=True
        ).start()


def analyze_weak_spots() -> Dict:
    logs = _load_logs()
    by_intent: Dict[str, List[float]] = {}
    for log in logs:
        intent = log.get("intent", "general")
        score = log.get("llm_score", log.get("h_score", log.get("confidence", 0.5)))
        by_intent.setdefault(intent, []).append(score)
    return {k: round(sum(v) / len(v), 2) for k, v in by_intent.items()}


def generate_report() -> str:
    spots = analyze_weak_spots()
    tips = _load_tips()
    if not spots:
        return "No response data yet."
    lines = ["📊 ASTRA Self-Improvement Report\n"]
    for intent, avg in sorted(spots.items(), key=lambda x: x[1]):
        bar = "🔴" if avg < 0.6 else ("🟡" if avg < 0.8 else "🟢")
        lines.append(f"{bar} {intent}: {avg:.0%}")
        if tips.get(intent):
            lines.append(f"   ⚠ {'; '.join(tips[intent][:2])}")
    return "\n".join(lines)


def auto_refine_prompts() -> str:
    try:
        import ollama

        weak = {k: v for k, v in analyze_weak_spots().items() if v < 0.7}
        tips = _load_tips()
        if not weak:
            return "All intents performing well."
        summary = "\n".join(
            [
                f"- {i} ({v:.0%}): {'; '.join(tips.get(i, ['no specific issues']))}"
                for i, v in weak.items()
            ]
        )
        resp = ollama.chat(
            model="phi3:mini",
            messages=[
                {
                    "role": "user",
                    "content": f"AI assistant has these issues:\n{summary}\n"
                    f"Suggest 3 concrete system prompt fixes. Each under 30 words. Format: 1. 2. 3.",
                }
            ],
            options={"temperature": 0.3, "num_predict": 200},
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        return f"Error: {e}"


class SelfImprovementEngine:
    def __init__(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def log_response(self, u, r, c, rating=None):
        log_response(u, r, c, rating)

    def analyze_weak_spots(self):
        return analyze_weak_spots()

    def generate_report(self):
        return generate_report()

    def auto_refine_prompts(self):
        return auto_refine_prompts()
