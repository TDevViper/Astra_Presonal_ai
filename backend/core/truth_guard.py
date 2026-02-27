
# ==========================================
# astra_engine/core/truth_guard.py
# ==========================================

import re
from typing import Tuple

class TruthGuard:
    """Prevents hallucinations and false claims."""
    
    FORBIDDEN_PATTERNS = [
        (r"you live in (?!delhi|gurugram)", "wrong_location"),
        (r"you are from (?!delhi|india)", "wrong_origin"),
        (r"your city is (?!delhi|gurugram)", "wrong_city"),
        (r"created by anthropic", "wrong_creator"),
        (r"made by anthropic", "wrong_creator"),
        (r"built by openai", "wrong_creator"),
        (r"i don't know (?:your|the user's) name", "name_hallucination"),
    ]
    
    SAFE_RESPONSES = {
        "wrong_location": "I don't have confirmed location info.",
        "wrong_origin": "I should verify that before saying.",
        "wrong_city": "I'm not certain about that.",
        "wrong_creator": "Arnav created me, actually!",
        "name_hallucination": "Your name is Arnav.",
        "default": "Let me be more careful with that answer."
    }
    
    def __init__(self):
        self.patterns = [
            (re.compile(p, re.IGNORECASE), vtype)
            for p, vtype in self.FORBIDDEN_PATTERNS
        ]
    
    def validate(self, reply: str) -> Tuple[bool, str]:
        """Check if reply violates truth."""
        for pattern, violation_type in self.patterns:
            if pattern.search(reply):
                return False, violation_type
        return True, ""
    
    def get_safe_reply(self, violation_type: str = "default") -> str:
        """Get safe replacement."""
        return self.SAFE_RESPONSES.get(violation_type, self.SAFE_RESPONSES["default"])

