#==========================================
# astra_engine/agents/react_agent.py
# ==========================================

def needs_react(user_input: str) -> bool:
    """Check if multi-step reasoning is needed."""
    react_keywords = [
        "think", "reason", "step by step", 
        "why", "how does", "explain how",
        "walk me through", "break down"
    ]
    text = user_input.lower()
    return any(word in text for word in react_keywords)


def react_solve(user_input: str) -> str:
    """
    Placeholder for ReAct agent.
    In production, this would call LLM with ReAct prompting.
    """
    return f"Let me think through this step by step: {user_input}"


def react(user_input: str) -> str:
    """Main ReAct entry point."""
    if needs_react(user_input):
        return react_solve(user_input)
    return user_input
