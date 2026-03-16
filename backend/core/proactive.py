import json
import os
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from collections import Counter

logger = logging.getLogger(__name__)

_BACKEND_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPISODES_FILE = os.path.join(_BACKEND_DIR, "memory", "data", "episodes.json")
PATTERNS_FILE = os.path.join(_BACKEND_DIR, "memory", "data", "patterns.json")


def _load_episodes() -> List[Dict]:
    if not os.path.exists(EPISODES_FILE):
        return []
    try:
        with open(EPISODES_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _load_patterns() -> Dict:
    if not os.path.exists(PATTERNS_FILE):
        return {"topics": {}, "last_session": None, "pending_tasks": []}
    try:
        with open(PATTERNS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"topics": {}, "last_session": None, "pending_tasks": []}


def _save_patterns(patterns: Dict) -> None:
    os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)
    with open(PATTERNS_FILE, "w") as f:
        json.dump(patterns, f, indent=2)


def analyze_patterns() -> Dict:
    episodes = _load_episodes()
    if not episodes:
        return {}

    stop_words = {
        "i", "a", "the", "is", "are", "was", "what", "how", "why",
        "do", "did", "can", "you", "me", "my", "about", "to", "in",
        "of", "and", "or", "for", "with", "it", "this", "that", "be",
        "explain", "tell", "show", "give", "make", "help", "please",
        "would", "could", "should", "does", "have", "has", "will",
        "want", "need", "think", "know", "understand", "using", "use"
    }

    word_counts: Counter   = Counter()
    intent_counts: Counter = Counter()

    for ep in episodes[-50:]:
        words = ep.get("user", "").lower().split()
        for w in words:
            w = w.strip(".,?!")
            if len(w) > 4 and w not in stop_words:
                word_counts[w] += 1
        if ep.get("intent"):
            intent_counts[ep["intent"]] += 1

    top_topics  = [w for w, _ in word_counts.most_common(5)]
    top_intents = [i for i, _ in intent_counts.most_common(3)]

    patterns = _load_patterns()
    patterns["topics"]        = dict(word_counts.most_common(10))
    patterns["top_topics"]    = top_topics
    patterns["top_intents"]   = top_intents
    patterns["last_session"]  = datetime.utcnow().isoformat()
    patterns["episode_count"] = len(episodes)
    _save_patterns(patterns)

    return patterns


def get_welcome_back(user_name: str = "User") -> Optional[str]:
    episodes = _load_episodes()
    if not episodes:
        return None

    last  = episodes[-3:]
    today = date.today().isoformat()

    if last[-1].get("date", "") == today:
        return None

    topics = []
    for ep in reversed(last):
        user_msg = ep.get("user", "")
        if len(user_msg) > 10:
            words = [w for w in user_msg.split() if len(w) > 5]
            if words:
                topics.append(words[0])

    topics = list(dict.fromkeys(topics))[:2]

    if topics:
        topic_str = " and ".join(topics)
        return (
            f"Welcome back, {user_name}! "
            f"Last time we were discussing {topic_str}. "
            f"Want to continue, or something new today?"
        )

    return f"Welcome back, {user_name}! What are we working on today?"


def get_proactive_suggestion(user_input: str, memory: Dict,
                              user_name: str = "User") -> Optional[str]:
    patterns     = analyze_patterns()
    topic_counts = patterns.get("topics", {})
    t            = user_input.lower()

    for word in t.split():
        if len(word) > 5 and topic_counts.get(word, 0) >= 3:
            return (
                f"💡 I've noticed you ask about '{word}' often. "
                f"Want me to build a summary or learning path for it?"
            )

    if any(w in t for w in ["code", "function", "class", "bug", "error"]):
        episodes       = _load_episodes()
        recent_intents = [e.get("intent") for e in episodes[-10:]]
        if "git_operation" not in recent_intents:
            return "💡 Working on code? I can check your git status if you want."

    tasks = memory.get("tasks", [])
    if tasks:
        pending = [task_item for task_item in tasks if task_item.get("status") == "todo"]
        if pending and len(pending) >= 2:
            return (
                f"💡 You have {len(pending)} pending tasks. "
                f"Want to review them?"
            )

    episodes  = _load_episodes()
    today_eps = [e for e in episodes if e.get("date") == date.today().isoformat()]
    if len(today_eps) >= 20:
        return "💡 You've been at this for a while. Take a break?"

    return None


def get_session_summary(user_name: str = "User") -> Optional[str]:
    episodes  = _load_episodes()
    today     = date.today().isoformat()
    today_eps = [e for e in episodes if e.get("date") == today]

    if not today_eps:
        return None

    intents = Counter(e.get("intent", "") for e in today_eps)
    top     = [i for i, _ in intents.most_common(3) if i]

    return (
        f"Today's session: {len(today_eps)} exchanges. "
        f"Main activities: {', '.join(top) if top else 'general chat'}. "
        f"Good work, {user_name}!"
    )


# ── System monitoring + WebSocket proactive alerts ──────────────────────
import threading, time, psutil

_broadcast_fn = None

def set_broadcast(fn):
    global _broadcast_fn
    _broadcast_fn = fn

def _broadcast(msg: str):
    if _broadcast_fn:
        try:
            _broadcast_fn(msg)
        except Exception as _e:
            logger.warning("error: %s", _e)

def start_proactive_monitor():
    threading.Thread(target=_monitor_loop, daemon=True).start()
    print("[Proactive] ✅ System monitor running (120s interval)")

def _monitor_loop():
    last_alerts = {}
    while True:
        try:
            _check_system(last_alerts)
            _check_tasks(last_alerts)
        except Exception as _e:
            logger.warning("error: %s", _e)
        time.sleep(120)

def _check_system(last_alerts: dict):
    now = time.time()

    cpu = psutil.cpu_percent(interval=None)
    if cpu > 85 and now - last_alerts.get("cpu", 0) > 300:
        _broadcast(f"⚠️ CPU is at {cpu:.0f}% — something's heating up.")
        last_alerts["cpu"] = now

    ram = psutil.virtual_memory().percent
    if ram > 90 and now - last_alerts.get("ram", 0) > 300:
        _broadcast(f"⚠️ RAM at {ram:.0f}% — memory pressure is high.")
        last_alerts["ram"] = now

    disk = psutil.disk_usage('/').percent
    if disk > 90 and now - last_alerts.get("disk", 0) > 600:
        _broadcast(f"💾 Disk at {disk:.0f}% — running low on space.")
        last_alerts["disk"] = now

    battery = psutil.sensors_battery()
    if battery and battery.percent < 20 and not battery.power_plugged:
        if now - last_alerts.get("battery", 0) > 300:
            _broadcast(f"🔋 Battery at {battery.percent:.0f}% — plug in soon.")
            last_alerts["battery"] = now

def _check_tasks(last_alerts: dict):
    now = time.time()
    if now - last_alerts.get("tasks", 0) < 1800:
        return
    try:
        mem_file = os.path.join(_BACKEND_DIR, "memory", "data", "memory.json")
        if not os.path.exists(mem_file):
            return
        with open(mem_file) as f:
            mem = json.load(f)
        tasks   = mem.get("tasks", [])
        pending = [t for t in tasks if t.get("status") == "todo"]
        if len(pending) >= 2:
            _broadcast(f"📌 You have {len(pending)} pending tasks. Want to review them?")
            last_alerts["tasks"] = now
    except Exception:
        pass  # TODO: handle
