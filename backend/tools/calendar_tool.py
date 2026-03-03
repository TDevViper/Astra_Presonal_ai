import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def get_todays_events() -> List[Dict]:
    """Get today's events using fast AppleScript date filter."""
    try:
        today = datetime.now().strftime("%A, %-d %B %Y")
        script = f'''
        tell application "Calendar"
            set theDate to date "{today}"
            set dayStart to theDate
            set dayEnd to theDate + 86400
            set result to ""
            repeat with c in (every calendar)
                set evs to (every event of c whose start date >= dayStart and start date < dayEnd)
                repeat with e in evs
                    set result to result & (summary of e) & "|" & ((start date of e) as string) & "|" & (name of c) & "||"
                end repeat
            end repeat
            return result
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15
        )
        return _parse_events(result.stdout.strip())
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        return []


def get_upcoming_events(hours: int = 2) -> List[Dict]:
    """Get events in the next N hours."""
    try:
        now_str    = datetime.now().strftime("%A, %-d %B %Y %H:%M:%S")
        future_secs = hours * 3600
        script = f'''
        tell application "Calendar"
            set nowDate to date "{now_str}"
            set futureDate to nowDate + {future_secs}
            set result to ""
            repeat with c in (every calendar)
                set evs to (every event of c whose start date >= nowDate and start date <= futureDate)
                repeat with e in evs
                    set result to result & (summary of e) & "|" & ((start date of e) as string) & "|" & (name of c) & "||"
                end repeat
            end repeat
            return result
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15
        )
        return _parse_events(result.stdout.strip())
    except Exception as e:
        logger.error(f"Upcoming events error: {e}")
        return []


def get_next_event() -> Optional[Dict]:
    events = get_upcoming_events(hours=8)
    return events[0] if events else None


def morning_briefing_text(user_name: str = "Arnav") -> str:
    events = get_todays_events()
    hour   = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"

    if not events:
        return f"{greeting}, {user_name}. No events on your calendar today. Clear day ahead."

    msg = f"{greeting}, {user_name}. You have {len(events)} event{'s' if len(events) > 1 else ''} today. "
    for i, e in enumerate(events[:3]):
        title = e['title']
        time  = e['time']
        msg += f"{'First up' if i == 0 else 'Then'}: {title}"
        if time:
            msg += f" at {time}"
        msg += ". "
    if len(events) > 3:
        msg += f"And {len(events) - 3} more."
    return msg


def reminder_check_text(user_name: str = "Arnav") -> Optional[str]:
    upcoming = get_upcoming_events(hours=1)
    if not upcoming:
        return None
    event = upcoming[0]
    title = event['title']
    time  = event['time']
    try:
        now      = datetime.now()
        event_dt = datetime.strptime(f"{now.date()} {time}", "%Y-%m-%d %I:%M %p")
        mins     = int((event_dt - now).total_seconds() / 60)
        if mins <= 0:
            return f"Hey {user_name}, {title} is happening right now."
        elif mins <= 10:
            return f"Hey {user_name}, {title} starts in {mins} minutes. Get ready."
        elif mins <= 30:
            return f"{user_name}, heads up — {title} in {mins} minutes."
        return None
    except Exception:
        return f"Hey {user_name}, you have {title} coming up at {time}."


def handle_calendar_command(text: str, user_name: str = "Arnav") -> Optional[str]:
    t = text.lower()
    if any(w in t for w in ["today's events", "my schedule", "what's on today", "calendar", "my meetings", "my day"]):
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
            return "No upcoming events in the next 8 hours."
        return f"Your next event is {event['title']} at {event['time']}."

    return None


def _parse_events(raw: str) -> List[Dict]:
    if not raw:
        return []
    events = []
    for item in raw.split("||"):
        item = item.strip()
        if not item:
            continue
        parts = item.split("|")
        if len(parts) >= 1 and parts[0].strip():
            events.append({
                "title":    parts[0].strip(),
                "time":     _parse_time(parts[1].strip()) if len(parts) > 1 else "",
                "calendar": parts[2].strip() if len(parts) > 2 else "Calendar"
            })
    events.sort(key=lambda x: x.get("time", ""))
    return events


def _parse_time(time_str: str) -> str:
    try:
        parts = time_str.strip().split()
        for part in parts:
            if ":" in part:
                h, m = part.split(":")[:2]
                hour = int(h)
                suffix = "AM" if hour < 12 else "PM"
                hour = hour % 12 or 12
                return f"{hour}:{m} {suffix}"
    except Exception:
        pass
    return time_str


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
    next_e = get_next_event()
    print(f"  {next_e}" if next_e else "  None upcoming")
