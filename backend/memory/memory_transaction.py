"""
memory/memory_transaction.py — Atomic memory write context manager.

Fixes the load-modify-save race condition where concurrent requests
overwrite each other's memory mutations.

Usage:
    with MemoryTransaction() as tx:
        memory = tx.memory          # snapshot loaded once
        memory["user_facts"].append(fact)
        tx.commit()                 # single atomic write at end
    # Outside the with block — write is done or rolled back
"""
import copy
import logging
import threading
from contextlib import contextmanager
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Module-level write lock — all transactions serialize on writes
_write_lock = threading.Lock()


class MemoryTransaction:
    def __init__(self):
        self._original: Dict[str, Any] = {}
        self.memory:    Dict[str, Any] = {}
        self._committed = False

    def __enter__(self):
        from memory.memory_engine import load_memory
        self._original = load_memory()
        self.memory    = copy.deepcopy(self._original)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.debug("MemoryTransaction rolled back due to exception: %s", exc_val)
        # Auto-commit if no exception and not already committed
        elif not self._committed:
            self.commit()
        return False  # don't suppress exceptions

    def commit(self):
        """Write memory atomically under the write lock."""
        if self._committed:
            return
        with _write_lock:
            from memory.memory_engine import save_memory
            save_memory(self.memory)
            self._committed = True
            logger.debug("MemoryTransaction committed")

    def discard(self):
        """Explicitly discard — don't write anything."""
        self._committed = True  # prevents auto-commit in __exit__
