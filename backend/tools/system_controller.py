# ==========================================
# tools/system_controller.py
# ASTRA Universal System Controller
# Controls every app on the Mac via voice
# ==========================================

import subprocess
import logging
import os
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# ── App name aliases ──────────────────────────────────────────
APP_ALIASES = {
    # Browsers
    "brave": "Brave Browser",
    "chrome": "Google Chrome",
    "firefox": "Firefox",
    "safari": "Safari",

    # Music
    "spotify": "Spotify",
    "apple music": "Music",
    "music": "Music",

    # Dev
    "android studio": "Android Studio",
    "iterm": "iTerm2",
    "terminal": "iTerm2",

    # Productivity
    "whatsapp": "WhatsApp",
    "notion": "Notion",
    "notes": "Notes",
    "keynote": "Keynote",
    "pages": "Pages",
    "numbers": "Numbers",
    "libreoffice": "LibreOffice",

    # Media
    "vlc": "VLC",

    # System
    "settings": "System Settings",
    "system settings": "System Settings",
    "finder": "Finder",
    "claude": "Claude",
    "ollama": "Ollama",
}

# Music apps with AppleScript support
MUSIC_APPS = ["Spotify", "Music", "VLC"]


# ══════════════════════════════════════════
# APP CONTROL
# ══════════════════════════════════════════

def open_app(app_name: str) -> str:
    """Open any app by name."""
    resolved = _resolve_app(app_name)
    try:
        subprocess.run(["open", "-a", resolved], check=True)
        logger.info(f"🚀 Opened: {resolved}")
        return f"Opening {resolved}."
    except Exception:
        # Try direct open
        try:
            subprocess.run(["open", f"/Applications/{resolved}.app"], check=True)
            return f"Opening {resolved}."
        except Exception as e:
            return f"Couldn't open {app_name}. Is it installed?"


def quit_app(app_name: str) -> str:
    """Quit any app."""
    resolved = _resolve_app(app_name)
    try:
        script = f'tell application "{resolved}" to quit'
        subprocess.run(["osascript", "-e", script], check=True)
        return f"Closed {resolved}."
    except Exception:
        return f"Couldn't close {app_name}."


def switch_to_app(app_name: str) -> str:
    """Bring app to foreground."""
    resolved = _resolve_app(app_name)
    try:
        script = f'tell application "{resolved}" to activate'
        subprocess.run(["osascript", "-e", script], check=True)
        return f"Switched to {resolved}."
    except Exception:
        return f"Couldn't switch to {app_name}."


def list_running_apps() -> str:
    """List all running apps."""
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of every process whose background only is false'],
            capture_output=True, text=True
        )
        apps = [a.strip() for a in result.stdout.strip().split(",")]
        return f"Running apps: {', '.join(apps)}"
    except Exception:
        return "Couldn't get running apps."


def open_url(url: str, browser: str = "Brave Browser") -> str:
    """Open a URL in browser."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        subprocess.run(["open", "-a", browser, url], check=True)
        return f"Opening {url} in {browser}."
    except Exception:
        subprocess.run(["open", url])
        return f"Opening {url}."


# ══════════════════════════════════════════
# MUSIC CONTROL
# ══════════════════════════════════════════

def _get_active_music_app() -> Optional[str]:
    """Find which music app is currently playing."""
    for app in MUSIC_APPS:
        try:
            result = subprocess.run(
                ["osascript", "-e", f'tell application "{app}" to get player state'],
                capture_output=True, text=True, timeout=2
            )
            state = result.stdout.strip()
            if state == "playing":
                return app
        except Exception:
            pass
    # Return first running music app
    for app in MUSIC_APPS:
        try:
            result = subprocess.run(
                ["osascript", "-e", f'tell application "System Events" to (name of processes) contains "{app}"'],
                capture_output=True, text=True, timeout=2
            )
            if "true" in result.stdout.lower():
                return app
        except Exception:
            pass
    return "Spotify"  # default


def play_pause(app: Optional[str] = None) -> str:
    app = app or _get_active_music_app()
    try:
        if app == "VLC":
            _osascript(f'tell application "VLC" to play')
        else:
            _osascript(f'tell application "{app}" to playpause')
        return f"Play/pause toggled on {app}."
    except Exception:
        return f"Couldn't control {app}."


def next_track(app: Optional[str] = None) -> str:
    app = app or _get_active_music_app()
    try:
        if app == "Spotify":
            _osascript('tell application "Spotify" to next track')
        elif app == "Music":
            _osascript('tell application "Music" to next track')
        elif app == "VLC":
            _osascript('tell application "VLC" to next')
        return f"Skipped to next track on {app}."
    except Exception:
        return "Couldn't skip track."


def previous_track(app: Optional[str] = None) -> str:
    app = app or _get_active_music_app()
    try:
        if app == "Spotify":
            _osascript('tell application "Spotify" to previous track')
        elif app == "Music":
            _osascript('tell application "Music" to previous track')
        return f"Previous track on {app}."
    except Exception:
        return "Couldn't go to previous track."


def get_now_playing(app: Optional[str] = None) -> str:
    app = app or _get_active_music_app()
    try:
        if app == "Spotify":
            name   = _osascript('tell application "Spotify" to get name of current track')
            artist = _osascript('tell application "Spotify" to get artist of current track')
        elif app == "Music":
            name   = _osascript('tell application "Music" to get name of current track')
            artist = _osascript('tell application "Music" to get artist of current track')
        else:
            return f"Can't get track info from {app}."
        return f"Playing '{name.strip()}' by {artist.strip()} on {app}."
    except Exception:
        return "Nothing playing right now."


def play_search(query: str, app: str = "Spotify") -> str:
    """Search and play on Spotify or Apple Music."""
    try:
        if app == "Spotify":
            script = f'''
            tell application "Spotify"
                activate
                search for "{query}"
                play
            end tell
            '''
            _osascript(script)
            return f"Searching for '{query}' on Spotify."
        elif app == "Music":
            script = f'''
            tell application "Music"
                activate
                search playlist "Library" for "{query}"
            end tell
            '''
            _osascript(script)
            return f"Searching for '{query}' on Apple Music."
        else:
            # Fallback: open YouTube Music in browser
            return open_url(f"https://music.youtube.com/search?q={query.replace(' ', '+')}")
    except Exception:
        return f"Couldn't play '{query}'."


# ══════════════════════════════════════════
# VOLUME & BRIGHTNESS
# ══════════════════════════════════════════

def set_volume(level: int) -> str:
    """Set system volume 0-100."""
    level = max(0, min(100, level))
    try:
        _osascript(f"set volume output volume {level}")
        return f"Volume set to {level}%."
    except Exception:
        return "Couldn't set volume."


def volume_up(step: int = 10) -> str:
    try:
        current = _get_volume()
        return set_volume(current + step)
    except Exception:
        return "Couldn't increase volume."


def volume_down(step: int = 10) -> str:
    try:
        current = _get_volume()
        return set_volume(max(0, current - step))
    except Exception:
        return "Couldn't decrease volume."


def mute() -> str:
    try:
        _osascript("set volume with output muted")
        return "Muted."
    except Exception:
        return "Couldn't mute."


def unmute() -> str:
    try:
        _osascript("set volume without output muted")
        return "Unmuted."
    except Exception:
        return "Couldn't unmute."


def _get_volume() -> int:
    try:
        result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True
        )
        return int(result.stdout.strip())
    except Exception:
        return 50


def _set_brightness_keys(level: int) -> str:
    steps = round(level / 100 * 16)
    for _ in range(16):
        subprocess.run(["osascript", "-e", "tell application "System Events" to key code 107"], capture_output=True)
    for _ in range(steps):
        subprocess.run(["osascript", "-e", "tell application "System Events" to key code 113"], capture_output=True)
    return f"Brightness set to {level}%."

def set_brightness(level: int) -> str:
    """Set screen brightness 0-100."""
    level = max(0, min(100, level))
    try:
        val = level / 100.0
        subprocess.run(["osascript", "-e", f'tell application "System Events"\n  tell process "SystemUIServer"\n    key code 144\n  end tell\nend tell'], capture_output=True)
        _osascript(f'set brightness of display 1 to {val}')
        return f"Brightness set to {level}%."
    except Exception:
        pass
    """Set screen brightness 0-100."""
    level = max(0, min(100, level))
    try:
        val = level / 100.0
        subprocess.run(["brightness", str(val)], check=True)
        return f"Brightness set to {level}%."
    except Exception:
        # Fallback via AppleScript
        try:
            _osascript(f'tell application "System Events" to key code 144')
            return f"Brightness adjusted."
        except Exception:
            return "Install 'brightness' cli: brew install brightness"


# ══════════════════════════════════════════
# SYSTEM ACTIONS
# ══════════════════════════════════════════

def lock_screen() -> str:
    try:
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to keystroke "q" using {command down, control down}'
        ])
        return "Screen locked."
    except Exception:
        return "Couldn't lock screen."


def sleep_display() -> str:
    try:
        subprocess.run(["pmset", "displaysleepnow"])
        return "Display sleeping."
    except Exception:
        return "Couldn't sleep display."


def take_screenshot(path: str = "~/Desktop/astra_screenshot.png") -> str:
    try:
        path = os.path.expanduser(path)
        subprocess.run(["screencapture", "-x", path], check=True)
        return f"Screenshot saved to {path}."
    except Exception:
        return "Couldn't take screenshot."


def get_battery() -> str:
    try:
        result = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if "%" in line:
                return f"Battery: {line.strip()}"
        return "Battery info unavailable."
    except Exception:
        return "Couldn't get battery info."


def get_wifi_status() -> str:
    try:
        result = subprocess.run(
            ["networksetup", "-getairportpower", "en0"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception:
        return "Couldn't get WiFi status."


def toggle_wifi(on: bool) -> str:
    state = "on" if on else "off"
    try:
        subprocess.run(["networksetup", "-setairportpower", "en0", state], check=True)
        return f"WiFi turned {state}."
    except Exception:
        return f"Couldn't turn WiFi {state}."


def empty_trash() -> str:
    try:
        _osascript('tell application "Finder" to empty trash')
        return "Trash emptied."
    except Exception:
        return "Couldn't empty trash."


def show_desktop() -> str:
    try:
        _osascript('tell application "System Events" to key code 103 using {command down}')
        return "Showing desktop."
    except Exception:
        return "Couldn't show desktop."


# ══════════════════════════════════════════
# VOICE COMMAND ROUTER
# ══════════════════════════════════════════

def handle_system_command(text: str) -> Optional[str]:
    """
    Parse natural language and route to correct system action.
    Returns response string or None if not a system command.
    """
    t = text.lower().strip()

    # ── Brightness (must be before music checks) ────────
    if "brightness" in t:
        import re
        match = re.search(r"(\d+)", t)
        if match:
            return set_brightness(int(match.group(1)))
        if "max" in t or "full" in t:
            return set_brightness(100)
        if "min" in t or "low" in t:
            return set_brightness(20)
        return set_brightness(70)

    # ── Music ─────────────────────────────
    if any(w in t for w in ["pause", "stop music", "stop song"]):
        return play_pause()
    if any(w in t for w in ["play music", "resume", "unpause"]):
        return play_pause()
    if any(w in t for w in ["next song", "next track", "skip"]):
        return next_track()
    if any(w in t for w in ["previous song", "prev track", "go back"]):
        return previous_track()
    if any(w in t for w in ["what's playing", "what is playing", "current song", "now playing"]):
        return get_now_playing()

    # Play search query
    if "play " in t:
        query = t.split("play ", 1)[-1].strip()
        query = query.replace(" on spotify", "").replace(" on apple music", "").replace(" on music", "").replace(" on youtube", "").strip()
        # Detect target app
        if "spotify" in query:
            query = query.replace("spotify", "").strip()
            return play_search(query, app="Spotify")
        elif "apple music" in query or "on music" in query:
            query = query.replace("apple music", "").replace("on music", "").strip()
            return play_search(query, app="Music")
        elif "youtube" in query:
            query = query.replace("youtube", "").replace("on", "").strip()
            return open_url(f"https://music.youtube.com/search?q={query.replace(' ', '+')}")
        else:
            return play_search(query)  # default Spotify

    # ── Volume ────────────────────────────
    if "volume up" in t or "louder" in t:
        return volume_up()
    if "volume down" in t or "quieter" in t or "lower volume" in t:
        return volume_down()
    if "mute" in t:
        return mute()
    if "unmute" in t:
        return unmute()
    if "volume" in t:
        import re
        match = re.search(r'volume\s+(\d+)', t)
        if match:
            return set_volume(int(match.group(1)))

    # ── Apps ──────────────────────────────
    if ("open " in t or "launch " in t or "start " in t) and len(t.split()) <= 6:
        app = t.replace("open ", "").replace("launch ", "").replace("start ", "").strip()
        # Check if it's a URL
        if "." in app and " " not in app:
            return open_url(app)
        return open_app(app)

    if "close " in t or "quit " in t:
        app = t.replace("close ", "").replace("quit ", "").strip()
        return quit_app(app)

    if "switch to " in t:
        app = t.replace("switch to ", "").strip()
        return switch_to_app(app)

    if "what apps are running" in t or "running apps" in t:
        return list_running_apps()

    # ── System ────────────────────────────
    if "lock" in t and "screen" in t:
        return lock_screen()
    if "sleep" in t and ("display" in t or "screen" in t):
        return sleep_display()
    if "screenshot" in t or "take a screenshot" in t:
        return take_screenshot()
    if "battery" in t:
        return get_battery()
    if "wifi on" in t or "turn on wifi" in t:
        return toggle_wifi(True)
    if "wifi off" in t or "turn off wifi" in t:
        return toggle_wifi(False)
    if "wifi" in t or "internet" in t:
        return get_wifi_status()
    if "empty trash" in t:
        return empty_trash()
    if "show desktop" in t:
        return show_desktop()


    return None  # Not a system command


# ── Helpers ───────────────────────────────────────────────────

def _osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=5
    )
    return result.stdout.strip()


def _resolve_app(name: str) -> str:
    name = name.lower().strip()
    return APP_ALIASES.get(name, name.title())


# ── Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🧪 Testing system controller...\n")

    print(get_battery())
    print(get_wifi_status())
    print(list_running_apps())
    print(get_now_playing())

    # Test command router
    tests = [
        "play lo-fi hip hop on spotify",
        "volume up",
        "what's playing", "brightness",
        "open brave",
        "battery",
        "take a screenshot",
        "next song",
    ]
    print("\n── Command routing test ──")
    for cmd in tests:
        result = handle_system_command(cmd)
        print(f"'{cmd}' → {result}")


SYSTEM_TRIGGERS = [
    "open ", "close ", "quit ", "launch ", "play ", "pause", "skip",
    "next song", "previous song", "volume", "mute", "unmute",
    "screenshot", "battery", "wifi", "lock screen", "sleep display",
    "switch to", "running apps", "empty trash", "what's playing", "brightness"
]

def is_system_command(text: str) -> bool:
    t = text.lower()
    return any(trigger in t for trigger in SYSTEM_TRIGGERS)
