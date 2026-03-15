# rag/watcher.py — Watch ~/ASTRA/docs/ and auto-ingest new files
import os
import time
import logging
import threading

logger    = logging.getLogger(__name__)
DOCS_DIR  = os.path.expanduser("~/ASTRA/docs")
_EXTS     = {".pdf", ".txt", ".md"}  # .py excluded — never index source code
_ingested = set()   # track already-processed files in this session
_thread   = None


def _scan_and_ingest():
    from rag.ingest import ingest_file
    os.makedirs(DOCS_DIR, exist_ok=True)
    for fname in os.listdir(DOCS_DIR):
        path = os.path.join(DOCS_DIR, fname)
        ext  = os.path.splitext(fname)[1].lower()
        if not os.path.isfile(path) or ext not in _EXTS:
            continue
        # Use (path, mtime) as cache key so re-saved files re-ingest
        key = (path, os.path.getmtime(path))
        if key in _ingested:
            continue
        try:
            n = ingest_file(path, tags=["docs", ext.strip(".")])
            logger.info(f"📄 Ingested '{fname}' → {n} chunks")
            _ingested.add(key)
        except Exception as e:
            logger.warning(f"Ingest failed for '{fname}': {e}")


def _watch_loop(interval: int):
    logger.info(f"📂 Doc watcher started — watching {DOCS_DIR}")
    while True:
        try:
            _scan_and_ingest()
        except Exception as e:
            logger.warning(f"Watcher scan error: {e}")
        time.sleep(interval)


def start_watcher(interval: int = 30):
    """Start background thread that checks DOCS_DIR every `interval` seconds."""
    global _thread
    if _thread and _thread.is_alive():
        return
    os.makedirs(DOCS_DIR, exist_ok=True)
    _thread = threading.Thread(target=_watch_loop, args=(interval,), daemon=True)
    _thread.start()
    logger.info(f"✅ Doc watcher running (interval={interval}s) — drop files into {DOCS_DIR}")


def ingest_now() -> dict:
    """Manually trigger a scan. Returns {filename: chunk_count}."""
    from rag.ingest import ingest_file
    os.makedirs(DOCS_DIR, exist_ok=True)
    results = {}
    for fname in os.listdir(DOCS_DIR):
        path = os.path.join(DOCS_DIR, fname)
        ext  = os.path.splitext(fname)[1].lower()
        if not os.path.isfile(path) or ext not in _EXTS:
            continue
        try:
            n = ingest_file(path, tags=["docs", ext.strip(".")])
            results[fname] = n
            key = (path, os.path.getmtime(path))
            _ingested.add(key)
        except Exception as e:
            results[fname] = f"error: {e}"
    return results
