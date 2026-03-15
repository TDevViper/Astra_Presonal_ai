import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_KNOWLEDGE_PATTERNS = [
    r"who\s+(invented|created|made|founded|discovered)",
    r"what\s+is\s+\w+",
    r"when\s+was",
    r"where\s+is",
    r"tell me about\s+\w+",
    r"explain\s+\w+",
    r"define\s+\w+",
    r"how does\s+\w+",
    r"what are\s+\w+",
    r"history of\s+\w+",
]


def needs_knowledge_query(user_text: str) -> bool:
    text = user_text.lower().strip()
    for p in _KNOWLEDGE_PATTERNS:
        if re.search(p, text):
            return True
    return False


def knowledge_lookup(query: str, memory: dict) -> Optional[str]:
    """
    Search the web and return a formatted answer.
    Falls back gracefully if search is unavailable.
    """
    try:
        from websearch.search import serper_search, format_results_for_llm
        results = serper_search(query, num_results=3)
        if not results:
            logger.warning("knowledge_lookup: no results from serper_search")
            return None
        formatted = format_results_for_llm(results, max_chars=1000)
        logger.info(f"knowledge_lookup: got {len(results)} results for '{query[:50]}'")
        return formatted
    except ImportError:
        logger.warning("knowledge_lookup: websearch module not available")
        return None
    except Exception as e:
        logger.warning(f"knowledge_lookup failed: {e}")
        return None


def knowledge(user_input: str, memory: dict = None) -> str:
    """
    Main knowledge agent entry point.
    Returns web search context if the query needs it, else returns the input unchanged.
    """
    if not needs_knowledge_query(user_input):
        return user_input

    logger.info(f"knowledge_agent: looking up '{user_input[:60]}'")
    result = knowledge_lookup(user_input, memory or {})

    if result:
        return f"[Web context for answering]\n{result}\n\n[User question]\n{user_input}"

    # Fallback — return original query if search unavailable
    return user_input
