# core/process_guardian.py
# JARVIS-level: monitors critical processes, auto-restarts crashed services,
# alerts on disk/memory pressure, compresses logs when disk is tight
import threading, time, subprocess, logging, os, shutil, gzip
from typing import Dict, Optional, Callable

logger       = logging.getLogger(__name__)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WATCHED_SERVICES = [
    {
        "name":     "ollama",
        "check":    lambda: _port_open(11434),
        "restart":  "ollama serve",
        "critical": True,
    },
    {
        "name":     "redis",
        "check":    lambda: _port_open(6379),
        "restart":  "redis-server --daemonize yes",
        "critical": False,
    },
]

_CHECK_INTERVAL = 30
_DISK_WARN_PCT  = 85
_DISK_CRIT_PCT  = 95
_RAM_WARN_PCT   = 85
_RAM_CRIT_PCT   = 95

_state: Dict = {
    "running":    False,
    "restarts":   {},
    "last_sweep": None,
    "alerts":     [],
}
_broadcast_fn: Optional[Callable] = None


def set_broadcast(fn: Callable):
    global _broadcast_fn
    _broadcast_fn = fn


def get_state() -> Dict:
    return dict(_state)


def _alert(msg: str):
    logger.warning("Guardian: %s", msg)
    _state["alerts"] = ([msg] + _state["alerts"])[:20]
    if _broadcast_fn:
        try:
            _broadcast_fn(msg)
        except Exception as _e:
            logger.debug('process_guardian: %s', _e)


def _port_open(port: int) -> bool:
    import socket
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except Exception:
        return False


def _restart_service(service: Dict) -> bool:
    name = service["name"]
    try:
        subprocess.Popen(service["restart"].split(),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        if service["check"]():
            _state["restarts"][name] = _state["restarts"].get(name, 0) + 1
            _alert(f"✅ Restarted {name} (#{_state['restarts'][name]})")
            return True
        _alert(f"❌ Failed to restart {name} — manual intervention needed")
        return False
    except Exception as e:
        _alert(f"❌ Restart error for {name}: {e}")
        return False


def _check_services():
    for svc in WATCHED_SERVICES:
        try:
            if not svc["check"]():
                _alert(f"💀 {svc['name']} is DOWN{'  (critical)' if svc['critical'] else ''}")
                _restart_service(svc)
        except Exception as e:
            logger.debug("service check error (%s): %s", svc["name"], e)


def _check_disk():
    try:
        total, used, free = shutil.disk_usage("/")
        pct = used / total * 100
        if pct >= _DISK_CRIT_PCT:
            _alert(f"🔴 Disk critically full: {pct:.0f}% — auto-compressing logs")
            _compress_logs()
        elif pct >= _DISK_WARN_PCT:
            _alert(f"⚠️ Disk at {pct:.0f}% — {round(free/1e9,1)}GB free")
    except Exception as e:
        logger.debug("disk check error: %s", e)


def _check_ram():
    try:
        import psutil
        pct = psutil.virtual_memory().percent
        if pct >= _RAM_CRIT_PCT:
            _alert(f"🔴 RAM at {pct:.0f}% — severe memory pressure")
        elif pct >= _RAM_WARN_PCT:
            _alert(f"⚠️ RAM at {pct:.0f}%")
    except Exception as e:
        logger.debug("ram check error: %s", e)


def _compress_logs():
    logs_dir = os.path.join(_BACKEND_DIR, "logs")
    if not os.path.isdir(logs_dir):
        return
    freed = 0
    for fname in os.listdir(logs_dir):
        if fname.endswith(".log") and not fname.endswith(".gz"):
            src = os.path.join(logs_dir, fname)
            dst = src + ".gz"
            try:
                size_before = os.path.getsize(src)
                with open(src, "rb") as f_in, gzip.open(dst, "wb") as f_out:
                    f_out.write(f_in.read())
                os.remove(src)
                freed += size_before - os.path.getsize(dst)
            except Exception as e:
                logger.warning("compress_logs failed for %s: %s", fname, e)
    if freed > 0:
        _alert(f"🗜️ Compressed logs — freed {round(freed/1e6, 1)}MB")


def _guardian_loop():
    while _state["running"]:
        try:
            _check_services()
            _check_disk()
            _check_ram()
            _state["last_sweep"] = time.time()
        except Exception as e:
            logger.error("guardian loop error: %s", e)
        time.sleep(_CHECK_INTERVAL)


def start(broadcast_fn: Optional[Callable] = None):
    if _state["running"]:
        return
    if broadcast_fn:
        set_broadcast(broadcast_fn)
    _state["running"] = True
    t = threading.Thread(target=_guardian_loop, daemon=True, name="process-guardian")
    t.start()
    logger.info("🛡️  Process guardian started (interval=%ds)", _CHECK_INTERVAL)


def stop():
    _state["running"] = False
