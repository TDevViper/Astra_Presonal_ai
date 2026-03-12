import os, logging
logger = logging.getLogger(__name__)

_DEFAULTS = {
    "web_search": True, "file_reader": True, "system_monitor": True,
    "task_manager": True, "git": True, "python_sandbox": True,
    "system_controller": True, "face_recognition": True,
    "smart_home": False, "screen_watcher": False, "device_discovery": False,
    "voice": True, "vision": True, "calendar": False,
}

class CapabilityManager:
    def __init__(self):
        self._flags = dict(_DEFAULTS)
        for key in self._flags:
            if os.getenv(f"ASTRA_DISABLE_{key.upper()}", "").strip() == "1":
                self._flags[key] = False

    def is_enabled(self, capability: str) -> bool:
        return self._flags.get(capability, False)

    def enable(self, capability: str) -> bool:
        if capability not in self._flags:
            return False
        self._flags[capability] = True
        return True

    def disable(self, capability: str) -> bool:
        if capability not in self._flags:
            return False
        self._flags[capability] = False
        return True

    def all_flags(self) -> dict:
        return dict(self._flags)

    def get_status(self) -> dict:
        cats = {
            "web_search":"search","file_reader":"files","python_sandbox":"execution",
            "git":"execution","system_monitor":"system","system_controller":"system",
            "task_manager":"productivity","calendar":"productivity","voice":"io",
            "vision":"io","face_recognition":"io","smart_home":"iot",
            "screen_watcher":"monitoring","device_discovery":"network",
        }
        return {"capabilities": {
            name: {"enabled": enabled, "category": cats.get(name, "general")}
            for name, enabled in self._flags.items()
        }}
