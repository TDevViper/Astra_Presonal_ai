#==========================================
# astra_engine/core/capabilities.py
# ==========================================

from typing import Dict

class CapabilityManager:
    """Manages system capabilities."""
    
    def __init__(self):
        self._capabilities = {
            "web_search": False,
            "file_read": True,
            "file_write": False,
            "python_exec": True,
            "memory_read": True,
            "memory_write": True,
        }
    
    def is_enabled(self, capability: str) -> bool:
        return self._capabilities.get(capability, False)
    
    def enable(self, capability: str) -> bool:
        if capability in self._capabilities:
            self._capabilities[capability] = True
            return True
        return False
    
    def disable(self, capability: str) -> bool:
        if capability in self._capabilities:
            self._capabilities[capability] = False
            return True
        return False
    
    def get_status(self) -> Dict[str, bool]:
        return self._capabilities.copy()