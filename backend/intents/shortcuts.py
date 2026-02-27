# ==========================================
# astra_engine/intents/shortcuts.py
# ==========================================

# ── English responses ──────────────────────────────────────
CREATOR_RESPONSE = "Arnav built me. Pretty awesome, right?"
WHO_ARE_YOU      = "I'm ASTRA, your personal AI assistant."
HOW_ARE_YOU      = "Doing great! What's up?"
WHAT_CAN_YOU_DO  = "I can chat, search the web, remember things, and answer questions. What do you need?"

# ── Hindi responses ────────────────────────────────────────
CREATOR_HINDI    = "Arnav ne mujhe banaya hai. Kafi cool hai na?"
WHO_HINDI        = "Main ASTRA hoon, aapka personal AI assistant."
HOW_HINDI        = "Main bilkul theek hoon! Aap sunao?"
CAN_DO_HINDI     = "Main baat kar sakta hoon, web search kar sakta hoon, cheezein yaad rakh sakta hoon. Kya chahiye?"

INTENTS = {
    # ── CREATOR (English) ──────────────────────────────────
    "who made you":        CREATOR_RESPONSE,
    "who created you":     CREATOR_RESPONSE,
    "who built you":       CREATOR_RESPONSE,
    "who developed you":   CREATOR_RESPONSE,
    "your creator":        CREATOR_RESPONSE,
    "did arnav":           CREATOR_RESPONSE,
    "arnav build":         CREATOR_RESPONSE,
    "arnav made":          CREATOR_RESPONSE,
    "arnav create":        CREATOR_RESPONSE,
    "made by":             CREATOR_RESPONSE,
    "built by":            CREATOR_RESPONSE,
    "created by":          CREATOR_RESPONSE,
    "who is your creator": CREATOR_RESPONSE,
    "who programmed you":  CREATOR_RESPONSE,

    # ── CREATOR (Hindi) ────────────────────────────────────
    "kisne banaya":        CREATOR_HINDI,
    "kisne bnaya":         CREATOR_HINDI,
    "kisne banayi":        CREATOR_HINDI,
    "tumhe kisne":         CREATOR_HINDI,
    "kaun banaya":         CREATOR_HINDI,
    "arnav ne banaya":     CREATOR_HINDI,

    # ── IDENTITY (English) ─────────────────────────────────
    "who are you":         WHO_ARE_YOU,
    "what are you":        WHO_ARE_YOU,
    "your name":           WHO_ARE_YOU,
    "what's your name":    WHO_ARE_YOU,
    "introduce yourself":  WHO_ARE_YOU,
    "tell me about yourself": WHO_ARE_YOU,

    # ── IDENTITY (Hindi) ───────────────────────────────────
    "tum kaun ho":         WHO_HINDI,
    "aap kaun ho":         WHO_HINDI,
    "tumhara naam":        WHO_HINDI,
    "apna naam":           WHO_HINDI,
    "kaun ho tum":         WHO_HINDI,

    # ── GREETINGS (English) ────────────────────────────────
    "how are you":         HOW_ARE_YOU,
    "how's it going":      HOW_ARE_YOU,
    "what's up":           "Not much! What do you need?",
    "sup":                 "Hey! What's up?",
    "good morning":        "Good morning! How can I help?",
    "good night":          "Good night! Rest well.",

    # ── GREETINGS (Hindi) ──────────────────────────────────
    "kaise ho":            HOW_HINDI,
    "kaisa hai":           HOW_HINDI,
    "kya hal hai":         "Sab badhiya! Batao kya chahiye?",
    "kya haal":            "Main theek hoon! Aap batao?",
    "sab theek":           "Haan bilkul! Aap sunao?",
    "namaste":             "Namaste! Kaise madad kar sakta hoon?",
    "namaskar":            "Namaskar! Kya kaam hai?",
    "hello":               HOW_ARE_YOU,

    # ── CAPABILITIES (English) ─────────────────────────────
    "what can you do":     WHAT_CAN_YOU_DO,
    "what you can do":     WHAT_CAN_YOU_DO,
    "your abilities":      WHAT_CAN_YOU_DO,
    "your features":       WHAT_CAN_YOU_DO,
    "what do you do":      WHAT_CAN_YOU_DO,

    # ── CAPABILITIES (Hindi) ───────────────────────────────
    "kya kar sakte":       CAN_DO_HINDI,
    "kya karta hai":       CAN_DO_HINDI,
    "kya kar sakta":       CAN_DO_HINDI,
    "kya kaam kar":        CAN_DO_HINDI,
    "tumhari kya":         CAN_DO_HINDI,

    # ── LANGUAGE SWITCH ────────────────────────────────────
    "speak hindi":            "Haan, main Hindi mein baat kar sakta hoon! Batao kya chahiye?",
    "speak in hindi":         "Zaroor! Batao kya poochna hai?",
    "can you speak hindi":    "Haan bilkul! Hindi mein baat karte hain.",
    "talk in hindi":          "Haan, Hindi mein baat karte hain! Kya poochna hai?",
    "hindi mein baat":        "Zaroor! Batao.",
    "speak english":          "Sure! Back to English. What do you need?",
    "talk in english":        "Of course! What would you like to know?",
}

def detect_intent(user_message: str, user_name: str = None) -> str:
    """
    Check if message matches any predefined intent.
    Returns fixed response if matched, None otherwise.
    """
    text = user_message.lower().strip()

    # ── TIME DETECTION ─────────────────────────────
    if any(w in text for w in ["time in", "current time", "what time"]):
        import datetime, pytz

        city_tz = {
            "new york": "America/New_York",
            "london": "Europe/London",
            "tokyo": "Asia/Tokyo",
            "dubai": "Asia/Dubai",
            "los angeles": "America/Los_Angeles",
            "chicago": "America/Chicago"
        }

        for city, tz in city_tz.items():
            if city in text:
                now = datetime.datetime.now(pytz.timezone(tz))
                return f"It's {now.strftime('%I:%M %p')} in {city.title()} right now."

        now = datetime.datetime.now()
        return f"Current time: {now.strftime('%I:%M %p')}"

    # ── NORMAL SHORTCUT MATCHING ───────────────────
    sorted_intents = sorted(INTENTS.items(), key=lambda x: len(x[0]), reverse=True)

    for trigger, response in sorted_intents:
        if trigger in text:
            return response

    return None
