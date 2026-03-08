import re

NO_SEARCH_PATTERNS = [
    r"\bcurrent (task|project|file|mode|status|session|song|track)\b",
    r"\bwhat.s the time\b",
    r"\bwhat time is it\b",
    r"\bmy (name|task|reminder|note|preference|list)\b",
    r"\bremind me\b",
    r"\bopen (file|folder|app|terminal)\b",
    r"\b(set|create|add|delete|remove) (task|reminder|note|alarm)\b",
    r"\bplay (music|song|spotify)\b",
    r"\bvolume (up|down)\b",
]

SEARCH_PATTERNS = [
    r"\b(latest|recent|new|current) (news|update|version|release|price|score)\b",
    r"\bwho is [A-Z][a-z]",
    r"\bweather (in|at|for)\b",
    r"\bprice of\b",
    r"\bwhat happened (to|with|in)\b",
    r"\b(today|tonight|this week).s\b",
    r"\bstock (price|market)\b",
    r"\bnews (about|on)\b",
    r"\bwhen (does|did|will).*(release|launch|open|close)\b",
    r"\bis .* still\b",
    r"\bwho won\b",
    r"\bscore of\b",
]

def should_search_web(user_input: str) -> bool:
    text = user_input.lower().strip()
    for pattern in NO_SEARCH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    for pattern in SEARCH_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    fallback_triggers = ["who is", "where is", "price of", "weather in", "news about"]
    return any(trigger in text for trigger in fallback_triggers)
