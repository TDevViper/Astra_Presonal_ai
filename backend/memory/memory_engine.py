#==========================================
# astra_engine/memory/memory_engine.py
# ==========================================

import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Path to memory file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(os.path.dirname(BASE_DIR), "memory.json")

DEFAULT_MEMORY = {
    "user_facts": [],
    "preferences": {
        "name": "Arnav",
        "location": None,
        "favorite_color": None
    },
    "conversation_summary": [],
    "emotional_patterns": {
        "last_emotion": {"label": "neutral", "score": 0.0},
        "history": [],
        "emotion_stats": {}
    }
}


def load_memory() -> Dict[str, Any]:
    """Load memory from file with error handling."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                # Ensure all required keys exist
                for key in DEFAULT_MEMORY:
                    if key not in memory:
                        memory[key] = DEFAULT_MEMORY[key]
                return memory
        except json.JSONDecodeError:
            logger.error("Memory file corrupted, resetting to default")
            return DEFAULT_MEMORY.copy()
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return DEFAULT_MEMORY.copy()
    
    return DEFAULT_MEMORY.copy()


def save_memory(memory: Dict[str, Any]) -> bool:
    """Save memory to file with error handling."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return False


def update_memory(memory: dict, category: str, key: str = None, value=None):
    """
    Update memory structure safely.
    
    Args:
        memory: Memory dict
        category: Category to update ('user_facts', 'preferences', etc.)
        key: Key within category (for dict categories)
        value: Value to set
    """
    if category not in memory:
        if category == "user_facts":
            memory[category] = []
        else:
            memory[category] = {}

    if category == "user_facts":
        # Append fact
        if isinstance(value, dict):
            memory["user_facts"].append(value)
    else:
        # Update dict-like category
        if key is None:
            raise ValueError("key required for non-list categories")
        if not isinstance(memory[category], dict):
            memory[category] = {}
        memory[category][key] = value

    return memory

