def memory_recall(user_message: str, memory: dict, user_name: str) -> str:
    """
    Check if user is asking about stored information.
    Only triggers for QUESTIONS, not statements.
    """
    text = user_message.lower().strip()
    
    # IMPORTANT: Only recall for questions, not statements
    # If user is TELLING us something (has "is", "are"), don't recall
    is_statement = any(phrase in text for phrase in [
        " is ", " are ", " was ", " were ",
        "my favorite", "my favourite", "i like", "i love"
    ])
    
    # If it's a statement, let it pass through to extraction
    if is_statement and not text.startswith(("what", "where", "who", "when", "why", "how")):
        return None

    # NAME RECALL
    if any(phrase in text for phrase in ["what's my name", "who am i", "do you know my name"]):
        name = memory.get("preferences", {}).get("name", user_name)
        return f"Your name is {name}!"

    # LOCATION RECALL - Questions only
    if any(phrase in text for phrase in ["where do i live", "where am i from", "what city"]):
        location = memory.get("preferences", {}).get("location")
        if location:
            return f"You live in {location}."
        return "I don't know where you live yet. Want to tell me?"

    # FAVORITE COLOR - Questions only
    if text.startswith(("what", "what's", "whats")) and "color" in text:
        # Check preferences first
        color = memory.get("preferences", {}).get("favorite_color")
        
        # If not in preferences, search user_facts
        if not color:
            facts = memory.get("user_facts", [])
            for fact in facts:
                if fact.get("type") == "preference" and "color" in fact.get("fact", "").lower():
                    color = fact.get("value")
                    break
        
        if color:
            return f"Your favorite color is {color}!"
        return "I don't know your favorite color yet. What is it?"

    # GENERAL PREFERENCES - Questions only
    if text.startswith(("what", "tell me")) and any(word in text for word in ["like", "prefer", "favorite", "favourite"]):
        prefs = memory.get("preferences", {})
        facts = memory.get("user_facts", [])
        
        pref_list = []
        
        # From preferences dict
        for key, val in prefs.items():
            if val and key != "name":
                pref_list.append(f"{key.replace('_', ' ')}: {val}")
        
        # From user_facts
        for fact in facts[-5:]:
            if fact.get("type") == "preference":
                pref_list.append(fact.get("fact", ""))
        
        if pref_list:
            return "Here's what I know you like: " + ", ".join(pref_list) + "."
        return "I haven't learned your preferences yet. Tell me what you like!"

    # GENERAL MEMORY QUERY
    if any(phrase in text for phrase in ["what do you know about me", "what you remember"]):
        facts = memory.get("user_facts", [])
        if not facts:
            return "I'm still learning about you! Tell me more."
        
        recent_facts = [f["fact"] for f in facts[-5:]]
        return "Here's what I remember: " + ", ".join(recent_facts) + "."

    return None