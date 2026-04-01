# ==========================================
# astra_engine/intents/shortcuts.py
# ==========================================

# ── English responses ──────────────────────────────────────
CREATOR_RESPONSE = "{user_name} built me. Pretty awesome, right?"
WHO_ARE_YOU = "I'm ASTRA, your personal AI assistant."
HOW_ARE_YOU = "Doing great! What's up?"
WHAT_CAN_YOU_DO = "I can chat, search the web, remember things, and answer questions. What do you need?"

# ── Hindi responses ────────────────────────────────────────
CREATOR_HINDI = "{user_name} ne mujhe banaya hai. Kafi cool hai na?"
WHO_HINDI = "Main ASTRA hoon, aapka personal AI assistant."
HOW_HINDI = "Main bilkul theek hoon! Aap sunao?"
CAN_DO_HINDI = "Main baat kar sakta hoon, web search kar sakta hoon, cheezein yaad rakh sakta hoon. Kya chahiye?"

INTENTS = {
    "what are you": "I'm ASTRA, your personal AI assistant.",
    "who are you": "I'm ASTRA, your personal AI assistant.",
    "what is astra": "I'm ASTRA, your personal AI assistant.",
    "who made you": "{user_name} built me. Pretty awesome, right?",
    "who built you": "{user_name} built me. Pretty awesome, right?",
    "who created you": "{user_name} built me. Pretty awesome, right?",
    # ── CREATOR (English) ──────────────────────────────────
    "did arnav": CREATOR_RESPONSE,
    "arnav build": CREATOR_RESPONSE,
    "arnav made": CREATOR_RESPONSE,
    "arnav create": CREATOR_RESPONSE,
    # ── CREATOR (Hindi) ────────────────────────────────────
    "kisne banaya": CREATOR_HINDI,
    "kisne bnaya": CREATOR_HINDI,
    "kisne banayi": CREATOR_HINDI,
    "tumhe kisne": CREATOR_HINDI,
    "kaun banaya": CREATOR_HINDI,
    "arnav ne banaya": CREATOR_HINDI,
    # ── IDENTITY (English) ─────────────────────────────────
    "your name": WHO_ARE_YOU,
    "what's your name": WHO_ARE_YOU,
    # ── IDENTITY (Hindi) ───────────────────────────────────
    "tum kaun ho": WHO_HINDI,
    "aap kaun ho": WHO_HINDI,
    "tumhara naam": WHO_HINDI,
    "apna naam": WHO_HINDI,
    "kaun ho tum": WHO_HINDI,
    # ── GREETINGS (English) ────────────────────────────────
    "how are you": HOW_ARE_YOU,
    "how's it going": HOW_ARE_YOU,
    "what's up": "Not much! What do you need?",
    "sup": "All good. What do you need?",
    "good morning": "Good morning! How can I help?",
    "good night": "Good night! Rest well.",
    "bye": "Bye! See you soon.",
    "goodbye": "Goodbye! Take care.",
    "see you": "See you!",
    "exit": "Closing chat. Bye!",
    "cya": "Cya!",
    "ok bye": "Bye!",
    "ok goodbye": "Goodbye!",
    # ── GREETINGS (Hindi) ──────────────────────────────────
    "kaise ho": HOW_HINDI,
    "kaisa hai": HOW_HINDI,
    "kya hal hai": "Sab badhiya! Batao kya chahiye?",
    "kya haal": "Main theek hoon! Aap batao?",
    "sab theek": "Haan bilkul! Aap sunao?",
    "namaste": "Namaste! Kaise madad kar sakta hoon?",
    "namaskar": "Namaskar! Kya kaam hai?",
    "hi": "Hey! What do you need?",
    "hello": HOW_ARE_YOU,
    "hey": "Hey! What can I do for you?",
    "hey what is up": "Not much! What's on your mind?",
    "hey what's up": "Not much! What do you need?",
    "what is up": "Not much! What do you need?",
    "whats up": "Not much! What do you need?",
    "wassup": "All good! What do you need?",
    "how is it going": "Going well! What can I help with?",
    "how's everything": "All systems nominal. What do you need?",
    "heyy": "Hey! What can I do for you?",
    # ── CAPABILITIES (English) ─────────────────────────────
    "what you can do": WHAT_CAN_YOU_DO,
    "your abilities": WHAT_CAN_YOU_DO,
    "your features": WHAT_CAN_YOU_DO,
    "what do you do": WHAT_CAN_YOU_DO,
    # ── CAPABILITIES (Hindi) ───────────────────────────────
    "kya kar sakte": CAN_DO_HINDI,
    "kya karta hai": CAN_DO_HINDI,
    "kya kar sakta": CAN_DO_HINDI,
    "kya kaam kar": CAN_DO_HINDI,
    "tumhari kya": CAN_DO_HINDI,
    # ── LANGUAGE SWITCH ────────────────────────────────────
    "speak hindi": "Haan, main Hindi mein baat kar sakta hoon! Batao kya chahiye?",
    "speak in hindi": "Zaroor! Batao kya poochna hai?",
    "can you speak hindi": "Haan bilkul! Hindi mein baat karte hain.",
    "talk in hindi": "Haan, Hindi mein baat karte hain! Kya poochna hai?",
    "hindi mein baat": "Zaroor! Batao.",
    "speak english": "Sure! Back to English. What do you need?",
    "talk in english": "Of course! What would you like to know?",
}


def _get_reminders(user_name):
    try:
        from memory.memory_engine import load_memory

        mem = load_memory()
        tasks = [t for t in mem.get("tasks", []) if t.get("status") == "todo"]
        if not tasks:
            return "You have no pending reminders or tasks."
        lines = ["• " + t.get("text", t.get("title", str(t))) for t in tasks[:5]]
        return "Your reminders:\n" + "\n".join(lines)
    except Exception as e:
        return f"Could not load reminders: {e}"


def detect_intent(user_message: str, user_name: str = None) -> str:
    """
    Check if message matches any predefined intent.
    Returns fixed response if matched, None otherwise.
    """
    text = user_message.lower().strip()

    # ── TIME DETECTION ─────────────────────────────
    if any(w in text for w in ["time in", "current time", "what time"]):
        import datetime
        import pytz

        city_tz = {
            "new york": "America/New_York",
            "london": "Europe/London",
            "tokyo": "Asia/Tokyo",
            "dubai": "Asia/Dubai",
            "los angeles": "America/Los_Angeles",
            "chicago": "America/Chicago",
        }

        for city, tz in city_tz.items():
            if city in text:
                now = datetime.datetime.now(pytz.timezone(tz))
                return f"It's {now.strftime('%I:%M %p')} in {city.title()} right now."

        now = datetime.datetime.now()
        return f"Current time: {now.strftime('%I:%M %p')}"

    # ── NORMAL SHORTCUT MATCHING ───────────────────
    # Block shortcuts from firing on tool commands
    # Game/chat requests — not music
    tl = text.lower()
    if any(
        p in tl
        for p in [
            "play game",
            "play a game",
            "lets play",
            "play with me",
            "play together",
        ]
    ):
        return "I can't play games yet, but I can chat, answer questions, or help with tasks!"

    if any(
        p in tl
        for p in [
            "my reminders",
            "show reminders",
            "my tasks",
            "what are my tasks",
            "do i have reminders",
        ]
    ):
        return _get_reminders(user_name)
    TOOL_PREFIXES = [
        "send",
        "message",
        "whatsapp",
        "play",
        "open",
        "close",
        "add task",
        "remind",
        "git",
        "run",
        "execute",
        "read file",
        "search",
    ]
    if any(text.startswith(p) for p in TOOL_PREFIXES):
        return None
    EXACT_ONLY = {
        "what are you",
        "who are you",
        "yo",
        "hi",
        "hey",
        "sup",
        "bye",
        "cya",
        "hello",
        "hii",
        "hiii",
        "ok",
        "okay",
        "yess",
        "yes",
        "no",
        "nope",
    }
    if text in EXACT_ONLY:
        response = INTENTS.get(text)
        if response:
            if user_name and "{user_name}" in response:
                response = response.replace("{user_name}", user_name)
            return response

    sorted_intents = sorted(
        [(k, v) for k, v in INTENTS.items() if len(k) > 3 and k not in EXACT_ONLY],
        key=lambda x: len(x[0]),
        reverse=True,
    )
    for trigger, response in sorted_intents:
        if trigger in text:
            if user_name and "{user_name}" in response:
                response = response.replace("{user_name}", user_name)
            return response

    # Vague catch-all
    vague = ["tell me things", "tell me something", "say something", "talk to me"]
    if any(text == v for v in vague):
        return "What do you want to know? Ask me something specific."
    return None
