import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODE_FILE    = os.path.join(_BACKEND_DIR, "memory", "data", "current_mode.json")
_current_mode = "jarvis"

MODES: Dict[str, Dict] = {
    "jarvis": {
        "name": "JARVIS", "description": "Default — sharp, direct, dry wit",
        "token_budget": {"casual":200,"technical":500,"coding":600,"default":250},
        "temperature": 0.65, "tts_speed": 1.1, "tts_voice": "af_bella",
        "model_bias": None, "system_addon": "", "emoji": "◈",
    },
    "focus": {
        "name": "FOCUS", "description": "Deep work — no small talk, long technical replies",
        "token_budget": {"casual":100,"technical":800,"coding":900,"default":600},
        "temperature": 0.3, "tts_speed": 1.2, "tts_voice": "am_michael",
        "model_bias": "mistral:latest", "emoji": "◉",
        "system_addon": "\n\nFOCUS MODE: No small talk. No preamble. For code: write full solutions. Be thorough.\n",
    },
    "chill": {
        "name": "CHILL", "description": "Relaxed — conversational, short replies",
        "token_budget": {"casual":80,"technical":200,"coding":300,"default":120},
        "temperature": 0.8, "tts_speed": 1.0, "tts_voice": "af_sarah",
        "model_bias": "phi3:mini", "emoji": "◌",
        "system_addon": "\n\nCHILL MODE: Be conversational and warm. 1-3 sentences max. No bullet points. Just talk.\n",
    },
    "expert": {
        "name": "EXPERT", "description": "PhD mode — deep dives, structured reasoning",
        "token_budget": {"casual":300,"technical":1000,"coding":900,"research":900,"default":700},
        "temperature": 0.2, "tts_speed": 1.05, "tts_voice": "bm_george",
        "model_bias": "mistral:latest", "emoji": "◆",
        "system_addon": "\n\nEXPERT MODE: Respond as a subject-matter expert. Structure: overview → details → edge cases. Show your work.\n",
    },
    "debug": {
        "name": "DEBUG", "description": "Engineering mode — diagnose everything",
        "token_budget": {"casual":200,"technical":700,"coding":900,"default":500},
        "temperature": 0.1, "tts_speed": 1.15, "tts_voice": "am_adam",
        "model_bias": "mistral:latest", "emoji": "⚙",
        "system_addon": "\n\nDEBUG MODE: Diagnose root cause first, then fix. Format: Problem → Root Cause → Fix → Prevention.\n",
    },
}

MODE_TRIGGERS = {
    "focus mode": "focus", "chill mode": "chill",
    "expert mode": "expert", "debug mode": "debug", "jarvis mode": "jarvis",
    "switch to focus": "focus", "switch to chill": "chill",
    "switch to expert": "expert", "switch to debug": "debug",
    "go focus": "focus", "go chill": "chill", "be chill": "chill", "focus up": "focus",
}


def _load_mode():
    global _current_mode
    try:
        if os.path.exists(_MODE_FILE):
            with open(_MODE_FILE) as f:
                _current_mode = json.load(f).get("mode", "jarvis")
    except Exception:
        _current_mode = "jarvis"


def _save_mode():
    try:
        os.makedirs(os.path.dirname(_MODE_FILE), exist_ok=True)
        with open(_MODE_FILE, "w") as f:
            json.dump({"mode": _current_mode}, f)
    except Exception:
        pass


_load_mode()


def get_current_mode() -> str:
    return _current_mode

def get_mode_config() -> Dict:
    return MODES.get(_current_mode, MODES["jarvis"])

def set_mode(mode: str) -> bool:
    global _current_mode
    if mode not in MODES:
        return False
    _current_mode = mode
    _save_mode()
    logger.info(f"Mode -> {mode.upper()}")
    return True

def detect_mode_switch(user_input: str) -> Optional[str]:
    t = user_input.lower().strip()
    for trigger, mode in MODE_TRIGGERS.items():
        if trigger in t:
            return mode
    return None

def get_token_budget(intent: str) -> int:
    budgets = get_mode_config().get("token_budget", {})
    return budgets.get(intent, budgets.get("default", 300))

def get_temperature() -> float:
    return get_mode_config().get("temperature", 0.65)

def get_tts_config() -> Dict:
    cfg = get_mode_config()
    return {"speed": cfg.get("tts_speed", 1.1), "voice": cfg.get("tts_voice", "af_bella")}

def get_model_bias() -> Optional[str]:
    return get_mode_config().get("model_bias")

def get_system_addon() -> str:
    return get_mode_config().get("system_addon", "")

def get_mode_banner() -> str:
    cfg = get_mode_config()
    return f"{cfg['emoji']} {cfg['name']} MODE — {cfg['description']}"

def list_modes() -> List[Dict]:
    return [
        {"id": mid, "name": cfg["name"], "description": cfg["description"],
         "emoji": cfg["emoji"], "active": mid == _current_mode}
        for mid, cfg in MODES.items()
    ]
