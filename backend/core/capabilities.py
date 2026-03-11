# core/capabilities.py
# Feature flags — controls which tools ASTRA can use
import os, logging
logger = logging.getLogger(__name__)

_DEFAULTS = {
    "web_search":        True,
    "file_reader":       True,
    "system_monitor":    True,
    "task_manager":      True,
    "git":               True,
    "python_sandbox":    True,
    "system_controller": True,   # OS/app control
    "smart_home":        False,  # requires Philips Hue / TinyTuya setup
    "screen_watcher":    False,  # resource intensive
    "device_discovery":  False,  # network scan
    "voice":             True,
    "vision":            True,
    "calendar":          False,  # requires macOS Calendar permission
}

class CapabilityManager:
    def __init__(self):
        self._flags = dict(_DEFAULTS)
        # Allow env overrides: ASTRA_DISABLE_VOICE=1
        for key in self._flags:
            env_key = f"ASTRA_DISABLE_{key.upper()}"
            if os.getenv(env_key, "").strip() == "1":
                self._flags[key] = False
                logger.info("Capability disabled via env: %s", key)

    def is_enabled(self, capability: str) -> bool:
        return self._flags.get(capability, False)

    def enable(self, capability: str):
        self._flags[capability] = True

    def disable(self, capability: str):
        self._flags[capability] = False

    def all_flags(self) -> dict:
        return dict(self._flags)
