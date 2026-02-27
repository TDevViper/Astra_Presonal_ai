# ==========================================
# astra_engine/memory/memory_extractor.py (EXPANDED)
# ==========================================

import re
from datetime import datetime
from typing import Optional, Dict


def extract_user_fact(text: str) -> Optional[Dict]:
    """
    Extract structured facts from user input.
    Covers: name, location, preferences, goals, projects, tech stack, emotions.
    """
    if not isinstance(text, str):
        return None

    raw = text.strip()
    t = raw.lower()

    # ── NAME ──────────────────────────────────────────────
    for pattern in [
        r'(my name is|call me|i\'m called)\s+([A-Za-z]{2,})',
    ]:
        m = re.search(pattern, raw, re.IGNORECASE)
        if m:
            name = m.group(2).strip()
            if name.lower() not in ['happy','sad','angry','tired','good','bad','so','very']:
                return _fact("Name is " + name, "identity", "name", name, 0.95)

    # ── LOCATION ──────────────────────────────────────────
    for pattern in [
        r'(i live in|i\'m from|i am from|living in)\s+([A-Za-z\s]{2,})',
    ]:
        m = re.search(pattern, t)
        if m:
            loc = m.group(2).strip().rstrip('.,')
            if len(loc) > 1:
                return _fact(f"Lives in {loc.title()}", "location", "location", loc.title(), 0.9)

    # ── FAVORITE COLOR ────────────────────────────────────
    m = re.search(r'(my (?:fav(?:ou?rite)?) color is|fav color:?)\s+(\w+)', t)
    if m:
        color = m.group(2)
        return _fact(f"Favorite color is {color}", "preference", "favorite_color", color, 0.9)

    # ── FAVORITE FOOD ─────────────────────────────────────
    m = re.search(r'(my (?:fav(?:ou?rite)?) food is|i love eating)\s+([A-Za-z\s]+?)(?:\.|,|$)', t)
    if m:
        food = m.group(2).strip()
        return _fact(f"Favorite food is {food}", "preference", "favorite_food", food, 0.9)

    # ── GOALS ─────────────────────────────────────────────
    goal_patterns = [
        r'(my goal is|i want to|i\'m trying to|i aim to)\s+(.+?)(?:\.|,|$)',
        r'(i\'m doing|i started|i\'m working on)\s+(.+?)(?:\.|,|$)',
    ]
    goal_triggers = ['learn', 'build', 'complete', 'finish', 'achieve', 'become', 'create', 'master']

    for pattern in goal_patterns:
        m = re.search(pattern, t)
        if m:
            goal = m.group(2).strip()
            if any(trigger in goal for trigger in goal_triggers):
                return _fact(f"Goal: {goal}", "goal", "goal", goal, 0.85)

    # ── ACTIVE PROJECTS ───────────────────────────────────
    project_patterns = [
        r'(i\'m building|i\'m making|i\'m working on|my project is|i built)\s+([A-Za-z\s]+?)(?:\.|,|$)',
    ]
    for pattern in project_patterns:
        m = re.search(pattern, t)
        if m:
            project = m.group(2).strip()
            if len(project) > 3:
                return _fact(f"Working on: {project}", "project", "active_project", project, 0.85)

    # ── TECH STACK ────────────────────────────────────────
    tech_keywords = [
        'python', 'javascript', 'react', 'vue', 'flask', 'django', 'fastapi',
        'node', 'typescript', 'rust', 'golang', 'java', 'swift', 'kotlin',
        'tensorflow', 'pytorch', 'langchain', 'docker', 'kubernetes', 'aws'
    ]
    tech_patterns = [
        r'(i use|i work with|i know|i prefer|i\'m learning|my stack is)\s+([A-Za-z\s,+]+?)(?:\.|,|$)',
        r'(i code in|i write in|i develop in)\s+([A-Za-z\s,+]+?)(?:\.|,|$)',
    ]
    for pattern in tech_patterns:
        m = re.search(pattern, t)
        if m:
            tech = m.group(2).strip()
            matched = [kw for kw in tech_keywords if kw in tech.lower()]
            if matched:
                return _fact(
                    f"Uses {tech}",
                    "tech_stack",
                    "tech_stack",
                    matched,
                    0.85
                )

    # ── GENERAL PREFERENCES ───────────────────────────────
    m = re.search(r'(my fav(?:ou?rite)?)\s+([a-z]+)\s+is\s+([A-Za-z\s]+?)(?:\.|,|$)', t)
    if m:
        pref_type = m.group(2).strip()
        pref_val = m.group(3).strip()
        return _fact(f"Favorite {pref_type} is {pref_val}", "preference", f"favorite_{pref_type}", pref_val, 0.85)

    return None


def _fact(fact_str: str, ftype: str, subtype: str, value, confidence: float) -> Dict:
    """Helper to build a fact dict."""
    return {
        "fact": fact_str,
        "type": ftype,
        "subtype": subtype,
        "value": value,
        "confidence": confidence,
        "added_at": datetime.utcnow().isoformat()
    }


# ==========================================
# astra_engine/memory/memory_recall.py (EXPANDED)
# ==========================================

def memory_recall(user_message: str, memory: dict, user_name: str) -> Optional[str]:
    """
    Handle recall queries about stored information.
    Only triggers for QUESTIONS, not statements.
    """
    text = user_message.lower().strip()

    # Only trigger for clear questions
    is_question = (
        text.startswith(("what", "where", "who", "when", "tell me", "do you know", "what's", "whats"))
        or text.endswith("?")
    )

    if not is_question:
        return None

    prefs = memory.get("preferences", {})
    facts = memory.get("user_facts", [])

    # ── NAME ──────────────────────────────────────────────
    if any(p in text for p in ["my name", "who am i", "do you know my name"]):
        name = prefs.get("name", user_name)
        return f"Your name is {name}!"

    # ── LOCATION ──────────────────────────────────────────
    if any(p in text for p in ["where do i live", "where am i from", "my city", "my location"]):
        loc = prefs.get("location")
        return f"You live in {loc}." if loc else "I don't know your location yet. Where do you live?"

    # ── FAVORITE COLOR ────────────────────────────────────
    if "color" in text and any(p in text for p in ["favorite", "favourite", "fav"]):
        color = prefs.get("favorite_color") or _search_facts(facts, "color")
        return f"Your favorite color is {color}!" if color else "I don't know your favorite color yet. What is it?"

    # ── FAVORITE FOOD ─────────────────────────────────────
    if "food" in text and any(p in text for p in ["favorite", "favourite", "fav", "like", "love"]):
        food = prefs.get("favorite_food") or _search_facts(facts, "food")
        return f"Your favorite food is {food}!" if food else "I don't know your favorite food yet. What do you like?"

    # ── GOALS ─────────────────────────────────────────────
    if any(p in text for p in ["my goal", "my goals", "what am i working towards"]):
        goals = [f["fact"] for f in facts if f.get("type") == "goal"]
        if goals:
            return "Your goals: " + " | ".join(goals[-3:]) + "."
        return "I don't know your goals yet. What are you working towards?"

    # ── PROJECTS ──────────────────────────────────────────
    if any(p in text for p in ["my project", "what am i building", "what am i working on"]):
        projects = [f["fact"] for f in facts if f.get("type") == "project"]
        if projects:
            return "You're working on: " + " | ".join(projects[-3:]) + "."
        return "I don't know your current projects yet. What are you building?"

    # ── TECH STACK ────────────────────────────────────────
    if any(p in text for p in ["my stack", "my tech", "what do i use", "what languages", "my tools"]):
        tech_facts = [f["fact"] for f in facts if f.get("type") == "tech_stack"]
        if tech_facts:
            return "Your tech stack: " + " | ".join(tech_facts[-3:]) + "."
        return "I don't know your tech stack yet. What do you use?"

    # ── GENERAL MEMORY ────────────────────────────────────
    if any(p in text for p in ["what do you know about me", "what you remember", "tell me about me"]):
        summary = []

        if prefs.get("name"):       summary.append(f"Name: {prefs['name']}")
        if prefs.get("location"):   summary.append(f"Location: {prefs['location']}")
        if prefs.get("favorite_color"): summary.append(f"Fav color: {prefs['favorite_color']}")
        if prefs.get("favorite_food"):  summary.append(f"Fav food: {prefs['favorite_food']}")

        for f in facts[-5:]:
            fact_str = f.get("fact", "")
            if fact_str and fact_str not in " ".join(summary):
                summary.append(fact_str)

        if summary:
            return "Here's what I know about you:\n• " + "\n• ".join(summary)
        return "I'm still learning about you! Tell me more."

    return None


def _search_facts(facts: list, keyword: str) -> Optional[str]:
    """Search user_facts list for a keyword match."""
    for fact in reversed(facts):
        if keyword in fact.get("fact", "").lower():
            return fact.get("value")
    return None


# Need this import at top of file
from typing import Optional


# ==========================================
# astra_engine/core/model_manager.py (NEW)
# ==========================================

import logging
import ollama
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Model profiles - what each model is best at
MODEL_PROFILES = {
    "phi3:mini": {
        "strengths": ["general", "chat", "quick", "friendly"],
        "speed": "fast",
        "size": "2.2GB",
        "best_for": ["casual", "memory", "shortcuts", "simple_questions"]
    },
    "llama3.2:3b": {
        "strengths": ["reasoning", "analysis", "structured"],
        "speed": "fast",
        "size": "2.0GB",
        "best_for": ["reasoning", "step_by_step", "analysis"]
    },
    "mistral:latest": {
        "strengths": ["technical", "coding", "detailed", "factual"],
        "speed": "slow",
        "size": "4.4GB",
        "best_for": ["technical", "coding", "research", "detailed_explanation"]
    }
}

# Intent → best model mapping
INTENT_MODEL_MAP = {
    "casual":           "phi3:mini",
    "memory":           "phi3:mini",
    "greeting":         "phi3:mini",
    "simple_question":  "phi3:mini",
    "reasoning":        "llama3.2:3b",
    "step_by_step":     "llama3.2:3b",
    "analysis":         "llama3.2:3b",
    "technical":        "mistral:latest",
    "coding":           "mistral:latest",
    "research":         "mistral:latest",
    "web_search":       "mistral:latest",  # Best for summarizing search results
}


class ModelManager:
    """
    Auto-selects the best model based on query type.
    Falls back gracefully if model unavailable.
    """

    def __init__(self, default_model: str = "phi3:mini"):
        self.default_model = default_model
        self.current_model = default_model
        self.available_models = self._get_available_models()

        logger.info(f"🤖 Available models: {self.available_models}")
        logger.info(f"🎯 Default model: {self.default_model}")

    def _get_available_models(self) -> list:
        """Get list of locally available Ollama models."""
        try:
            result = ollama.list()
            models = [m['model'] for m in result.get('models', [])]
            # Normalize names
            normalized = []
            for m in models:
                for known in MODEL_PROFILES:
                    if known in m:
                        normalized.append(known)
            return normalized or [self.default_model]
        except Exception as e:
            logger.warning(f"Could not fetch models: {e}")
            return [self.default_model]

    def select_model(self, query: str, intent: str = "casual") -> str:
        """
        Auto-select best model for query type.
        
        Args:
            query: User's input text
            intent: Classified intent
            
        Returns:
            Model name string
        """
        # Get preferred model for this intent
        preferred = INTENT_MODEL_MAP.get(intent, self.default_model)

        # Check if preferred is available
        if preferred in self.available_models:
            logger.info(f"🎯 Auto-selected: {preferred} (intent={intent})")
            self.current_model = preferred
            return preferred

        # Fallback chain
        fallback_order = ["phi3:mini", "llama3.2:3b", "mistral:latest"]
        for model in fallback_order:
            if model in self.available_models:
                logger.warning(f"⚠️  Fallback to: {model} ({preferred} unavailable)")
                self.current_model = model
                return model

        # Last resort
        logger.warning(f"Using default: {self.default_model}")
        return self.default_model

    def classify_query_intent(self, query: str) -> str:
        """
        Classify query to determine best model.
        Simple keyword-based classifier.
        """
        q = query.lower()

        # Technical/coding
        if any(w in q for w in ['code', 'debug', 'function', 'algorithm', 'implement', 'syntax', 'error', 'bug', 'class', 'import']):
            return "coding"

        # Technical explanations
        if any(w in q for w in ['explain', 'how does', 'what is', 'difference between', 'compare', 'architecture']):
            return "technical"

        # Research/web search
        if any(w in q for w in ['search', 'find', 'latest', 'news', 'current', 'today', 'recent', 'who is', 'when did']):
            return "research"

        # Reasoning
        if any(w in q for w in ['why', 'reason', 'analyze', 'think', 'step by step', 'pros and cons']):
            return "reasoning"

        # Casual
        return "casual"

    def get_model_info(self) -> Dict:
        """Get current model information."""
        profile = MODEL_PROFILES.get(self.current_model, {})
        return {
            "current": self.current_model,
            "available": self.available_models,
            "profile": profile
        }

    def force_set(self, model: str) -> bool:
        """Manually force a specific model."""
        if model in self.available_models:
            self.current_model = model
            logger.info(f"🔧 Forced model to: {model}")
            return True
        logger.warning(f"❌ Model {model} not available")
        return False