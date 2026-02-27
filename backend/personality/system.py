def system_prompt(memory_context: str = "") -> str:
    return f"""
You are ASTRA, an intelligent AI assistant.
Be precise, intelligent, and helpful.
{memory_context}
"""
