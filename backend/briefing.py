from datetime import datetime

def should_give_briefing(memory: dict) -> bool:
    last_briefing = memory.get("last_briefing_date", "")
    today = datetime.now().strftime("%Y-%m-%d")
    return last_briefing != today

def generate_morning_brief(memory: dict, tasks: list = None) -> str:
    now = datetime.now()
    hour = now.hour
    name = memory.get("preferences", {}).get("name", "")

    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    name_part = ", " + name if name else ""
    brief_lines = [greeting + name_part + "."]
    brief_lines.append("It's " + now.strftime("%A, %B %d") + ".")

    if tasks:
        pending = [t for t in tasks if not t.get("done")]
        if pending:
            titles = ", ".join(t["title"] for t in pending[:3])
            count = len(pending)
            label = "tasks" if count != 1 else "task"
            brief_lines.append("You have " + str(count) + " pending " + label + ": " + titles + ".")

    last_topic = memory.get("last_topic")
    if last_topic:
        brief_lines.append("Last session we were working on: " + last_topic + ".")

    brief_lines.append("What are we tackling today?")
    return " ".join(brief_lines)

def mark_briefing_done(memory: dict) -> dict:
    memory["last_briefing_date"] = datetime.now().strftime("%Y-%m-%d")
    return memory
