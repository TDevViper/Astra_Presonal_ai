
# ==========================================
# astra_engine/agents/knowledge_agent.py
# ==========================================

import re
from typing import Optional

def needs_knowledge_query(user_text: str) -> bool:
    """
    Detect if query requires external knowledge lookup.
    """
    text = user_text.lower().strip()

    patterns = [
        r"who\s+(invented|created|made|founded)",
        r"what\s+is\s+\w+",
        r"when\s+was",
        r"where\s+is",
        r"tell me about\s+\w+",
        r"explain\s+\w+",
        r"define\s+\w+"
    ]

    for p in patterns:
        if re.search(p, text):
            return True

    return False


def knowledge_lookup(query: str, memory: dict) -> Optional[str]:
    """
    Perform knowledge lookup.
    Currently returns None - integrate with web search in production.
    """
    # TODO: Integrate with websearch/search.py
    # from websearch.search import duckduckgo_search
    # result = duckduckgo_search(query)
    # return result
    
    return None


def knowledge(user_input: str) -> str:
    """Main knowledge agent entry point."""
    if needs_knowledge_query(user_input):
        # In production, call knowledge_lookup
        return f"Let me look that up: {user_input}"
    return user_input

