# astra_engine/emotion/emotion_detector.py

import re
from typing import Tuple

EMOTION_KEYWORDS = {
    "sad": ["sad", "depressed", "down", "unhappy", "sucks", "lonely", "miserable", "upset", "blue", "cry"],
    "angry": ["angry", "mad", "furious", "pissed", "hate", "annoyed", "irritated", "frustrated", "rage"],
    "joy": ["happy", "great", "awesome", "amazing", "excited", "glad", "yay", "wonderful", "fantastic", "love", "enjoy", "pleased", "delighted"],
    "anxious": ["anxious", "anxiety", "nervous", "worried", "scared", "afraid", "stress", "tense", "panic"],
    "tired": ["tired", "exhausted", "sleepy", "drained", "fatigue", "weary", "worn"],
    "surprised": ["surprised", "shocked", "wow", "whoa", "omg", "can't believe", "unbelievable"],
}


def normalize(text: str) -> str:
    """Normalize text for emotion detection."""
    return re.sub(r"[^\w\s']", " ", (text or "").lower())


def detect_emotion(text: str) -> Tuple[str, float]:
    """
    Detect emotion from text using keyword matching.
    
    Returns:
        (emotion_label, confidence_score)
        
    Labels: sad, angry, joy, anxious, tired, surprised, neutral
    Score: 0.0 to 1.0
    """
    normalized = normalize(text)
    
    if not normalized.strip():
        return "neutral", 0.0

    words = normalized.split()
    counts = {}

    # Count matches for each emotion
    for label, keywords in EMOTION_KEYWORDS.items():
        count = 0
        for keyword in keywords:
            # Word boundary check
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, normalized)
            count += len(matches)
        counts[label] = count

    # Find dominant emotion
    best_label = "neutral"
    best_count = 0
    
    for label, count in counts.items():
        if count > best_count:
            best_count = count
            best_label = label

    # Calculate confidence score
    if best_count == 0:
        return "neutral", 0.0
    
    # More aggressive scoring
    base_score = min(1.0, (best_count / max(1, len(words))) * 2.0)
    
    # Boost if multiple matches
    if best_count > 1:
        base_score = min(1.0, base_score * 1.5)
    
    # Lower threshold
    if base_score < 0.01:
        return "neutral", 0.0

    return best_label, round(base_score, 2)