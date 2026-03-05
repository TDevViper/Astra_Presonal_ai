import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Only check these calendars — skip India Holidays (too many events)
CALENDARS_TO_CHECK = ["Home", "Work", "Scheduled Reminders"]


def _get_all_events(calendar: str) -> List[Dict]:
    """Get all events from a single calendar — fast, no date filter in AppleScript."""
    try:
        script = f'''
tell application "Calendar"
    tell calendar "{calendar}"
        set output to ""
        repeat with e in (every event)
            set output to output & (summary of e) & "|" & ((start date of e) as string) & "||"
        end repeat
        return output
    end tell
end tell
'''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        raw = result.stdout.strip()
        if not raw:
            return []

        events = []
        for item in raw.split("||"):
            item = item.strip()
            if not item:
                continue
            parts = item.split("|")
            if len(parts) >= 2 and parts[0].strip():
                events.append({
                    "title":    parts[0].strip(),
                    "raw_time": parts[1].strip(),
                    "calendar": calendar
                })
        return events
    except Exception as e:
        logger.error(f"Error fetching {calendar}: {e}")
        return []


def _parse_raw_time(raw: str) -> Optional[datetime]:
    """Parse AppleScript date string like 'Tuesday, 3 March 2026 at 8:13:30 PM'"""
    try:
        # Remove day name
        parts = raw.split(", ", 1)
        date_part = parts[1] if len(parts) > 1 else parts[0]
        # Remove 'at'
        date_part = date_part.replace(" at ", " ")
        return datetime.strptime(date_part.strip(), "%d %B %Y %I:%M:%S %p")
    except Exception:
        try:
            return datetime.strptime(raw.strip(), "%A, %d %B %Y at %I:%M:%S %p")
        except Exception:
            return None


def get_todays_events() -> List[Dict]:
    today = datetime.now().date()
    events = []
    for cal in CALENDARS_TO_CHECK:
        for e in _get_all_events(cal):
            dt = _parse_raw_time(e["raw_time"])
            if dt and dt.date() == today:
                events.append({
                    "title":    e["title"],
                    "time":     dt.strftime("%I:%M %p").lstrip("0"),
                    "calendar": e["calendar"],
                    "dt":       dt
                })
    events.sort(key=lambda x: x["dt"])
    return events


def get_upcoming_events(hours: int = 2) -> List[Dict]:
    now    = datetime.now()
    events = []
    for cal in CALENDARS_TO_CHECK:
        for e in _get_all_events(cal):
            dt = _parse_raw_time(e["raw_time"])
            if dt and now <= dt <= datetime(now.year, now.month, now.day, now.hour, now.minute) \
                    .replace(hour=now.hour) and (dt - now).total_seconds() <= hours * 3600:
                events.append({
                    "title":    e["title"],
                    "time":     dt.strftime("%I:%M %p").lstrip("0"),
                    "calendar": e["calendar"],
                    "dt":       dt
                })
    events.sort(key=lambda x: x["dt"])
    return events


def get_next_event() -> Optional[Dict]:
    now    = datetime.now()
    events = []
    for cal in CALENDARS_TO_CHECK:
        for e in _get_all_events(cal):
            dt = _parse_raw_time(e["raw_time"])
            if dt and dt > now:
                events.append({
                    "title":    e["title"],
                    "time":     dt.strftime("%I:%M %p").lstrip("0"),
                    "calendar": e["calendar"],
                    "dt":       dt
                })
    if not events:
        return None
    events.sort(key=lambda x: x["dt"])
    return events[0]


def morning_briefing_text(user_name: str = "Arnav") -> str:
    events = get_todays_events()
    hour   = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    if not events:
        return f"{greeting}, {user_name}. No events on your calendar today. Clear day ahead."

    msg = f"{greeting}, {user_name}. You have {len(events)} event{'s' if len(events) > 1 else ''} today. "
    for i, e in enumerate(events[:3]):
        msg += f"{'First up' if i == 0 else 'Then'}: {e['title']} at {e['time']}. "
    if len(events) > 3:
        msg += f"And {len(events) - 3} more."
    return msg


def reminder_check_text(user_name: str = "Arnav") -> Optional[str]:
    now    = datetime.now()
    events = []
    for cal in CALENDARS_TO_CHECK:
        for e in _get_all_events(cal):
            dt = _parse_raw_time(e["raw_time"])
            if dt and 0 <= (dt - now).total_seconds() <= 3600:
                events.append({"title": e["title"], "dt": dt})
    if not events:
        return None
    events.sort(key=lambda x: x["dt"])
    e    = events[0]
    mins = int((e["dt"] - now).total_seconds() / 60)
    if mins <= 0:
        return f"Hey {user_name}, {e['title']} is happening right now."
    elif mins <= 10:
        return f"Hey {user_name}, {e['title']} starts in {mins} minutes. Get ready."
    elif mins <= 30:
        return f"{user_name}, heads up — {e['title']} in {mins} minutes."
    return None


def handle_calendar_command(text: str, user_name: str = "Arnav") -> Optional[str]:
    t = text.lower()
    if any(w in t for w in ["today's events", "my schedule", "what's on today",
                             "calendar", "my meetings", "my day", "what do i have"]):
        events = get_todays_events()
        if not events:
            return "Nothing on your calendar today."
        reply = f"You have {len(events)} event{'s' if len(events) > 1 else ''} today: "
        for e in events[:4]:
            reply += f"{e['title']} at {e['time']}, "
        return reply.rstrip(", ") + "."

    if any(w in t for w in ["next meeting", "next event", "what's next"]):
        event = get_next_event()
        if not event:
            return "No upcoming events."
        return f"Your next event is {event['title']} at {event['time']}."

    return None


if __name__ == "__main__":
    print("📅 Testing Calendar Tool...")
    print("\nToday's events:")
    events = get_todays_events()
    if events:
        for e in events:
            print(f"  • {e['title']} at {e['time']} ({e['calendar']})")
    else:
        print("  No events today")
    print("\nMorning briefing:")
    print(morning_briefing_text())
    print("\nNext event:")
    e = get_next_event()
    print(f"  {e['title']} at {e['time']}" if e else "  None")
