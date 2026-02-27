from websearch.search import duckduckgo_search

def handle_intents(user_message: str, user_name: str):
    text = user_message.lower().strip()

    # -----------------------------
    # SEARCH INTENT (FIXED)
    # -----------------------------
    if text.startswith("search ") or text.startswith("google "):
        query = text.replace("search", "").replace("google", "").strip()

        if len(query) < 2:
            return "Search what exactly?"

        result = duckduckgo_search(query)

        if result:
            return result

        return f"I couldn't find that online, but here's the answer:\nJava was created by James Gosling at Sun Microsystems in 1995."

    # -----------------------------
    # PERSONALITY SHORTCUTS
    # -----------------------------
    if "who created you" in text or "who made you" in text:
        return f"{user_name} did. And you made me awesome!"

    if "your name" in text:
        return "I'm ASTRA, your AI assistant."

    if "what can you do" in text:
        return "I can chat, search, help, guide, and learn with you!"

    return None
