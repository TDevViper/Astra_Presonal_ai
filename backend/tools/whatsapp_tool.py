import subprocess
import logging
import time
import re
from typing import Optional

logger = logging.getLogger(__name__)

CONTACTS = {
    "Mummy":    "Mummy",
    "dad":    "Dad",
    "mother": "Mom",
    "father": "Dad",
}


def send_whatsapp_message(contact: str, message: str) -> str:
    try:
        # Just use the name directly — no lookup needed
        resolved = contact.title()
        logger.info(f"📱 Sending WhatsApp to {resolved}: {message}")

        subprocess.run(["open", "-a", "WhatsApp"], check=True)
        time.sleep(2)

        script = f'''
tell application "WhatsApp" to activate
delay 1.5
tell application "System Events"
    tell process "WhatsApp"
        -- Open search with Cmd+K (search for chat)
        keystroke "f" using command down
        delay 1.5

        -- Clear and type contact name
        keystroke "a" using command down
        delay 0.3
        keystroke "{resolved}"
        delay 3

        -- Press down arrow twice to reach first chat result
        key code 125
        delay 0.3
        key code 125
        delay 0.3

        -- Press Enter to open it
        key code 36
        delay 2

        -- Tab to focus message input
        key code 48
        delay 0.5

        -- Type message
        keystroke "{message}"
        delay 0.5

        -- Send
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
            logger.error(f"WhatsApp error: {result.stderr.strip()}")
            return f"Couldn't send to {resolved}. Make sure they exist in WhatsApp."

    except Exception as e:
        logger.error(f"WhatsApp error: {e}")
        return f"Failed: {e}"


def handle_whatsapp_command(text: str) -> Optional[str]:
    t = text.lower().strip()

    triggers = ["message ", "whatsapp ", "send ", "text ", "msg "]
    if not any(tr in t for tr in triggers):
        return None

    for trigger in triggers:
        if trigger in t:
            t = t.replace(trigger, "", 1).strip()
            break

    if t.startswith("to "):
        t = t[3:].strip()

    contact = None
    message = None

    for alias in CONTACTS:
        if t.lower().startswith(alias + " "):
            contact = alias
            message = t[len(alias):].strip()
            break

    if not contact:
        parts   = t.split(" ", 1)
        contact = parts[0].strip()
        message = parts[1].strip() if len(parts) > 1 else ""

    if not contact:
        return "Who should I send the message to?"
    if not message:
        return f"What should I say to {contact}?"

    return send_whatsapp_message(contact, message)


def add_contact(alias: str, whatsapp_name: str) -> str:
    CONTACTS[alias.lower()] = whatsapp_name
    return f"Added: '{alias}' → '{whatsapp_name}'"


if __name__ == "__main__":
    print("📱 Testing — sending ONE message to Mom...")
    result = send_whatsapp_message("mom", "test from ASTRA")
    print(result)
