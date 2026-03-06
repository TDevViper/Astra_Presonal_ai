import subprocess
import logging
import time
import re
from typing import Optional

logger = logging.getLogger(__name__)

CONTACTS = {
    "mummy": "Mummy",
    "dad":   "Dad",
    "mom":   "Mom",
    "papa":  "Papa",
}

# STRICT triggers — must have both "send/message" AND a contact name
# Prevents "tell me about this" from triggering WhatsApp
WHATSAPP_TRIGGERS = ["whatsapp", "send whatsapp", "send message to", "message to"]

def handle_whatsapp_command(text: str) -> Optional[str]:
    t = text.lower().strip()

    # STRICT check — must explicitly say whatsapp or "send message to"
    if not any(tr in t for tr in WHATSAPP_TRIGGERS):
        return None

    # Must have a known contact or "to <name>" pattern
    has_contact = any(alias in t for alias in CONTACTS)
    has_to      = " to " in t

    if not has_contact and not has_to:
        return None

    # Extract contact + message
    contact = None
    message = None

    for alias, name in CONTACTS.items():
        if alias in t:
            contact = name
            # Get message after contact name
            idx     = t.index(alias) + len(alias)
            message = text[idx:].strip().lstrip(",:- ")
            break

    if not contact:
        # Try "to <name> <message>"
        match = re.search(r'to ([a-zA-Z]+)\s+(.*)', t)
        if match:
            contact = match.group(1).title()
            message = match.group(2).strip()

    if not contact:
        return "Who should I send the message to?"
    if not message:
        return f"What should I say to {contact}?"

    return send_whatsapp_message(contact, message)


def send_whatsapp_message(contact: str, message: str) -> str:
    try:
        resolved = contact.title()
        logger.info(f"📱 Sending WhatsApp to {resolved}: {message}")

        subprocess.run(["open", "-a", "WhatsApp"], check=True)
        time.sleep(2)

        script = f'''
tell application "WhatsApp" to activate
delay 1.5
tell application "System Events"
    tell process "WhatsApp"
        keystroke "f" using command down
        delay 1.5
        keystroke "a" using command down
        delay 0.3
        keystroke "{resolved}"
        delay 3
        key code 125
        delay 0.3
        key code 125
        delay 0.3
        key code 36
        delay 2
        key code 48
        delay 0.5
        keystroke "{message}"
        delay 0.5
        key code 36
    end tell
end tell
'''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=20
        )

        if result.returncode == 0:
            return f"Message sent to {resolved}: '{message}'"
        else:
            return f"Couldn't send to {resolved}. Make sure they exist in WhatsApp."

    except Exception as e:
        logger.error(f"WhatsApp error: {e}")
        return f"Failed: {e}"


def add_contact(alias: str, whatsapp_name: str) -> str:
    CONTACTS[alias.lower()] = whatsapp_name
    return f"Added: '{alias}' → '{whatsapp_name}'"
