#==========================================
# astra_engine/emotion/emotion_responder.py
# ==========================================

import random
from typing import Optional, Dict


def choose_reply(
    emotion_label: str,
    score: float,
    user_name: str = None,
    memory: Optional[Dict] = None
) -> str:
    """
    Generate empathetic response based on detected emotion.
    
    Args:
        emotion_label: Detected emotion
        score: Confidence score
        user_name: User's name for personalization
        memory: Memory dict for context
        
    Returns:
        Empathetic response string
    """
    # Base responses for each emotion
    responses = {
        "sad": [
            "That sounds tough. I'm here for you.",
            "I'm sorry you're feeling down.",
            "Want to talk about it?",
        ],
        "angry": [
            "I get why you're frustrated.",
            "That sounds annoying. Want to vent?",
            "I understand why that would upset you.",
        ],
        "anxious": [
            "That seems stressful. Let's break it down.",
            "Take a breath. We'll figure this out.",
            "I'm here to help with whatever's worrying you.",
        ],
        "joy": [
            "Love that energy!",
            "That's awesome!",
            "Glad you're feeling great!",
        ],
        "tired": [
            "Rest if you can. You deserve it.",
            "Take a break if you need one.",
            "Sounds like you need some downtime.",
        ],
        "surprised": [
            "Whoa! Didn't see that coming!",
            "That's unexpected!",
            "Wow, really?",
        ],
        "neutral": [
            "Got it.",
            "Alright.",
            "I'm listening.",
        ]
    }

    # Select random response for variety
    reply = random.choice(responses.get(emotion_label, responses["neutral"]))

    # Personalize with name (if available and not generic)
    if user_name and user_name.lower() not in ["friend", "user", "buddy", "anonymous"]:
        reply = f"{reply} {user_name}."

    # Add emotional insight occasionally (20% chance)
    if memory and random.random() < 0.20:
        patterns = memory.get("emotional_patterns", {})
        stats = patterns.get("emotion_stats", {})
        
        emotion_count = stats.get(emotion_label, {}).get("count", 0)
        
        if emotion_count > 3 and emotion_label != "neutral":
            insights = {
                "sad": "You've been feeling down lately.",
                "angry": "You seem frustrated often.",
                "anxious": "You've been stressed quite a bit.",
                "tired": "You've been exhausted lately.",
            }
            
            if emotion_label in insights:
                reply += f" {insights[emotion_label]}"

    return reply