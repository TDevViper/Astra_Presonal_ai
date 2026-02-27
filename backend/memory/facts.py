# backend/astra_engine/memory/facts.py

def extract_facts(conversation: list) -> dict:
    """
    Minimal extraction: find 'I am X' style lines in the last messages.
    Returns: {"user_facts": [...], "preferences": {...}}
    """
    facts = []
    prefs = {}
    for m in reversed(conversation[-10:]):
        t = m.get("content", "")
        if "i am " in t.lower():
            # crude extract
            after = t.lower().split("i am ", 1)[1].split()[0]
            facts.append(f"User name might be {after}")
    return {"user_facts": facts, "preferences": prefs}
