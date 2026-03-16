import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 300
BREAK_INTERVAL = 90 * 60
MORNING_HOUR   = 9
EVENING_HOUR   = 21
USER_NAME = "User"  # overridden at runtime from memory


class ProactiveEngine:
    def __init__(self, speak_fn: Callable[[str], None]):
        self.speak = speak_fn
        try:
            import json, os as _os
            _mem_path = _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                "memory", "data", "memory.json"
            )
            if _os.path.exists(_mem_path):
                with open(_mem_path) as _f:
                _m = json.load(_f)
                global USER_NAME
                USER_NAME = _m.get("preferences", {}).get("name", "User")
        except Exception as e:
            logger.warning("ProactiveEngine: calendar tool unavailable: %s", e)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_break_reminder = datetime.now()
        self._focus_start: Optional[datetime] = None
        self._fired_today: set = set()
        self._last_spoke: Optional[datetime] = None
        logger.info("🧠 ProactiveEngine initialized")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("🚀 ProactiveEngine started")

    def stop(self):
        self._running = False
        logger.info("🛑 ProactiveEngine stopped")

    def start_focus_session(self):
        self._focus_start = datetime.now()
        self.speak(f"Focus session started. I'll remind you to take a break in 90 minutes, {USER_NAME}.")

    def end_focus_session(self):
        if self._focus_start:
            elapsed = int((datetime.now() - self._focus_start).total_seconds()) // 60
            pass  # disabled
        self._focus_start = None

    def _loop(self):
        time.sleep(CHECK_INTERVAL)  # wait before first check
        while self._running:
            try:
                self._check_triggers()
            except Exception as e:
                logger.error(f"ProactiveEngine loop error: {e}")
            time.sleep(CHECK_INTERVAL)

    def _check_triggers(self):
        now    = datetime.now()
        hour   = now.hour
        minute = now.minute

        if hour == 0 and minute < 2:
            self._fired_today.clear()

        if hour == MORNING_HOUR and "morning" not in self._fired_today:
            self._fired_today.add("morning")
            self._do_morning_briefing(now)

        elif hour == 12 and minute >= 30 and "midday" not in self._fired_today:
            self._fired_today.add("midday")
            self.speak(f"Hey {USER_NAME}, it's lunchtime. Don't forget to eat and step away from the screen.")

        elif hour == 15 and "afternoon" not in self._fired_today:
            self._fired_today.add("afternoon")
            self._do_afternoon_checkin()

        elif hour == EVENING_HOUR and "evening" not in self._fired_today:
            self._fired_today.add("evening")
            self._do_evening_wrapup()

        elif hour == 1 and "latenight" not in self._fired_today:
            self._fired_today.add("latenight")
            self.speak(f"{USER_NAME}, it's past 1 AM. You should get some sleep. I'll be here tomorrow.")

        self._check_break_reminder(now)
        self._check_calendar_reminder(now)

        if hour % 3 == 0 and minute < 2:
            key = f"tasks_{hour}"
            if key not in self._fired_today:
                self._fired_today.add(key)
                self._check_pending_tasks()

    def _do_morning_briefing(self, now: datetime):
        greeting = _time_greeting(now.hour)
        tasks    = _get_pending_tasks()
        msg      = f"{greeting}, {USER_NAME}! "

        # Add calendar events
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from tools.calendar_tool import get_todays_events
            events = get_todays_events()
            if events:
                msg += f"You have {len(events)} event{'s' if len(events) > 1 else ''} today. First up: {events[0]['title']} at {events[0]['time']}. "
            else:
                msg += "Clear calendar today. "
        except Exception as e:
            logger.warning("ProactiveEngine: calendar tool unavailable: %s", e)

        if tasks:
            msg += f"You have {len(tasks)} task{'s' if len(tasks) > 1 else ''} pending. Top priority: {tasks[0]['title']}. "

        msg += "Let's make it a great day."
        self.speak(msg)

    def _do_afternoon_checkin(self):
        tasks = _get_pending_tasks()
        if tasks:
            msg = f"Hey {USER_NAME}, afternoon check-in. {len(tasks)} task{'s' if len(tasks) > 1 else ''} still pending. Keep going."
        else:
            msg = ""  # disabled
        self.speak(msg)

    def _do_evening_wrapup(self):
        tasks = _get_pending_tasks()
        if tasks:
            msg = f"Evening wrap-up, {USER_NAME}. {len(tasks)} task{'s' if len(tasks) > 1 else ''} left. '{tasks[0]['title']}' is top priority for tomorrow. Time to wind down."
        else:
            msg = f"Evening wrap-up, {USER_NAME}. All tasks done — solid work today. Rest up."
        self.speak(msg)

    def _check_break_reminder(self, now: datetime):
        elapsed = (now - self._last_break_reminder).total_seconds()
        if elapsed >= BREAK_INTERVAL:
            self._last_break_reminder = now
            self.speak(f"Hey {USER_NAME}, stand up, stretch, grab some water. You've earned it.")

    def _check_pending_tasks(self):
        tasks = _get_pending_tasks(priority="high")
        if tasks:
            self.speak(f"Heads up {USER_NAME} — high priority task waiting: {tasks[0]['title']}.")

    def _check_calendar_reminder(self, now: datetime):
        try:
            if self._last_spoke and (now - self._last_spoke).total_seconds() < 10 * 60:
                return
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from tools.calendar_tool import reminder_check_text
            reminder = reminder_check_text(USER_NAME)
            if reminder:
                self._last_spoke = now
                self.speak(reminder)
        except Exception as e:
            logger.error(f"Calendar reminder error: {e}")


def _get_pending_tasks(priority: Optional[str] = None):
    try:
        import json, os
        memory_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "memory", "data", "memory.json"
        )
        if not os.path.exists(memory_path):
            return []
        with open(memory_path) as f:
            memory = json.load(f)
        tasks = [t for t in memory.get("tasks", []) if t.get("status") == "todo"]
        if priority:
            tasks = [t for t in tasks if t.get("priority") == priority]
        return tasks
    except Exception as e:
        logger.error(f"Failed to load tasks: {e}")
        return []


def _time_greeting(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    return "Good evening"


_engine_instance: Optional[ProactiveEngine] = None

def get_proactive_engine(speak_fn: Callable[[str], None]) -> ProactiveEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ProactiveEngine(speak_fn=speak_fn)
    return _engine_instance


if __name__ == "__main__":
    import sys, subprocess
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def speak_blocking(text):
        print(f"🔊 {text}")
        import platform; (subprocess.run(["say", "-v", "Samantha", "-r", "185", text]) if platform.system() == "Darwin" else print(f"[TTS] {text[:80]}"))

    print("🧠 Testing ProactiveEngine...")
    engine = ProactiveEngine(speak_fn=speak_blocking)
    engine.speak("ASTRA proactive engine online.")
    engine._do_morning_briefing(datetime.now())
    engine._do_afternoon_checkin()
    engine._last_break_reminder = datetime.now() - timedelta(minutes=91)
    engine._check_break_reminder(datetime.now())
    engine._do_evening_wrapup()
    print("✅ All triggers tested")
