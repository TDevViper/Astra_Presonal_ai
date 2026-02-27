# ==========================================
# memory/memory_extractor.py
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
            if name.lower() not in ['happy', 'sad', 'angry', 'tired', 'good', 'bad', 'so', 'very']:
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

    # ── FAVORITE LANGUAGE ─────────────────────────────────  ✅ NEW
    m = re.search(
        r'my (?:fav(?:ou?rite)?|preferred)\s+(?:programming\s+)?language is\s+([A-Za-z+#]+)',
        t
    )
    if m:
        lang = m.group(1).strip()
        return _fact(
            f"Favorite programming language is {lang.title()}",
            "preference", "favorite_language", lang.title(), 0.95
        )

    # ── FAVORITE LANGUAGE ─────────────────────────────────
    m = re.search(r'my (?:fav(?:ou?rite)?|preferred)\s+(?:programming\s+)?language is\s+([A-Za-z+#]+)', t)
    if m:
        lang = m.group(1).strip()
        return _fact(f"Favorite programming language is {lang.title()}", "preference", "favorite_language", lang.title(), 0.95)

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
                return _fact(f"Uses {tech}", "tech_stack", "tech_stack", matched, 0.85)

    # ── GENERAL PREFERENCES ───────────────────────────────
    m = re.search(r'(my fav(?:ou?rite)?)\s+([a-z]+)\s+is\s+([A-Za-z\s]+?)(?:\.|,|$)', t)
    if m:
        pref_type = m.group(2).strip()
        pref_val  = m.group(3).strip()
        return _fact(f"Favorite {pref_type} is {pref_val}", "preference", f"favorite_{pref_type}", pref_val, 0.85)

    return None


def _fact(fact_str: str, ftype: str, subtype: str, value, confidence: float) -> Dict:
    return {
        "fact":       fact_str,
        "type":       ftype,
        "subtype":    subtype,
        "value":      value,
        "confidence": confidence,
        "added_at":   datetime.utcnow().isoformat()
    }