# ==========================================
# astra_engine/core/truth_guard.py
# ==========================================

import re
from typing import Tuple


class TruthGuard:
    """
    Prevents hallucinations and false claims.
    Reads user info from memory at runtime — not hardcoded.
    """

    STATIC_FORBIDDEN = [
        (r"created by anthropic", "wrong_creator"),
        (r"made by anthropic", "wrong_creator"),
        (r"built by openai", "wrong_creator"),
        (r"i am chatgpt", "wrong_creator"),
        (r"i am gpt", "wrong_creator"),
    ]

    def __init__(self, user_name: str = "", user_location: str = ""):
        self.user_name = user_name
        self.user_location = user_location
        self._compile_patterns()

    def _compile_patterns(self):
        patterns = list(self.STATIC_FORBIDDEN)

        # Dynamic location guard — only if location is known
        if self.user_location:
            loc = re.escape(self.user_location.lower())
            patterns += [
                (rf"you live in (?!{loc})", "wrong_location"),
                (rf"your city is (?!{loc})", "wrong_city"),
            ]

        # Name hallucination guard
        patterns.append(
            (r"i don.t know (?:your|the user.s) name", "name_hallucination")
        )

        self.patterns = [(re.compile(p, re.IGNORECASE), vtype) for p, vtype in patterns]

    def update_user_info(
        self, user_name: "str | None" = None, user_location: "str | None" = None
    ):
        """Call this when memory updates with new user info."""
        if user_name:
            self.user_name = user_name
        if user_location is not None:
            self.user_location = user_location
        self._compile_patterns()

    def validate(self, reply: str) -> Tuple[bool, str]:
        """Check if reply violates truth."""
        for pattern, violation_type in self.patterns:
            if pattern.search(reply):
                return False, violation_type
        return True, ""

    def get_safe_reply(self, violation_type: str = "default") -> str:
        """Get safe replacement."""
        safe = {
            "wrong_location": f"I'm not sure where {self.user_name} lives — I'll wait until they confirm.",
            "wrong_city": "I'm not certain about that location.",
            "wrong_creator": f"I'm ASTRA — a personal AI system built by {self.user_name}, running fully locally on your machine.",
            "name_hallucination": f"Your name is {self.user_name}.",
            "default": "Let me be more careful with that answer.",
        }
        return safe.get(violation_type, safe["default"])
