#==========================================
# astra_engine/intents/classifier.py
# ==========================================

def is_question_like(text: str) -> bool:
    """
    Check if text looks like a question.
    """
    if not text:
        return False
    
    text = text.strip().lower()
    
    # Question words
    question_words = [
        "what", "how", "why", "who", "when", "where",
        "which", "whose", "whom", "explain", "tell me",
        "define", "describe", "can you", "could you",
        "would you", "should i"
    ]
    
    # Ends with question mark
    if text.endswith("?"):
        return True
    
    # Starts with question word
    for word in question_words:
        if text.startswith(word + " "):
            return True
    
    return False


SEARCH_KEYWORDS = [
    "search", "lookup", "google", "find",
    "who is", "what is", "when did", "where is",
    "search for", "look up", "find out"
]


def is_search_query(text: str) -> bool:
    """
    Check if text is requesting a web search.
    """
    text = text.lower()
    return any(keyword in text for keyword in SEARCH_KEYWORDS)


def classify_intent(text: str) -> str:
    """
    Classify user intent into categories.
    
    Returns:
        - 'search': User wants web search
        - 'question': User is asking a question
        - 'statement': User is making a statement
        - 'command': User is giving a command
    """
    text = text.strip()
    
    if not text:
        return 'unknown'
    
    if is_search_query(text):
        return 'search'
    
    if is_question_like(text):
        return 'question'
    
    # Command indicators
    command_words = ['create', 'make', 'build', 'write', 'generate', 'show me']
    if any(text.lower().startswith(word) for word in command_words):
        return 'command'
    
    return 'statement'