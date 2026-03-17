# core/smart_guardian.py — Intelligent system health scoring
import psutil
import subprocess
import platform
import logging
import threading
import time
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)

_broadcast_fn: Optional[Callable] = None

def set_broadcast(fn: Callable):
    global _broadcast_fn
    _broadcast_fn = fn

def _broadcast(msg: str):
    if _broadcast_fn:
        try: _broadcast_fn(msg)
        except Exception: pass


def get_swap_mb() -> float:
    try:
        swap = psutil.swap_memory()
        return swap.used / (1024 * 1024)
    except Exception:
        return 0.0


def get_memory_pressure() -> float:
    """
    Returns 0.0 (healthy) to 1.0 (critical).
    Uses macOS memory_pressure command when available,
    falls back to swap-based heuristic.
    """
    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(
                ["memory_pressure"], text=True, timeout=3
            )
            for line in out.splitlines():
                if "System-wide memory free percentage" in line:
                    pct = float(line.split(":")[-1].strip().rstrip("%"))
                    return round(1.0 - pct / 100, 3)
        except Exception:
            pass
    # Fallback — use swap as proxy
    swap_mb = get_swap_mb()
    if swap_mb < 100:   return 0.1
    if swap_mb < 300:   return 0.4
    if swap_mb < 600:   return 0.6
    return 0.85


def get_compression_ratio() -> float:
    """Pages compressed / pages active — high ratio = normal on macOS."""
    try:
        vm = psutil.virtual_memory()
        return round(vm.percent / 100, 2)
    except Exception:
        return 0.5


def health_score(stats: Dict) -> int:
    """
    Score 0–100. Higher = healthier.
    Based on swap, memory pressure, CPU — not raw free RAM.
    """
    score = 100

    # Swap — real indicator of memory stress
    swap_mb = stats.get("swap_mb", 0)
    if swap_mb > 800:  score -= 40
    elif swap_mb > 400: score -= 25
    elif swap_mb > 150: score -= 10

    # Memory pressure — macOS native metric
    pressure = stats.get("memory_pressure", 0)
    if pressure > 0.8:  score -= 35
    elif pressure > 0.6: score -= 20
    elif pressure > 0.4: score -= 8

    # CPU
    cpu = stats.get("cpu_percent", 0)
    if cpu > 90: score -= 20
    elif cpu > 75: score -= 10

    # Disk
    disk = stats.get("disk_percent", 0)
    if disk > 95: score -= 10
    elif disk > 85: score -= 4

    return max(0, score)


def get_full_stats() -> Dict:
    vm    = psutil.virtual_memory()
    disk  = psutil.disk_usage("/")
    cpu   = psutil.cpu_percent(interval=0.5)
    swap  = get_swap_mb()
    press = get_memory_pressure()
    score = health_score({
        "swap_mb": swap,
        "memory_pressure": press,
        "cpu_percent": cpu,
        "disk_percent": disk.percent,
    })

    level = "healthy" if score >= 80 else "warning" if score >= 55 else "critical"

    return {
        "score":            score,
        "level":            level,
        "cpu_percent":      cpu,
        "ram_percent":      vm.percent,
        "ram_available_gb": round(vm.available / 1024**3, 1),
        "swap_mb":          round(swap, 0),
        "memory_pressure":  press,
        "disk_percent":     disk.percent,
    }


def smart_message(stats: Dict) -> Optional[str]:
    """Generate an intelligent, contextual alert — not just a raw metric."""
    score = stats["score"]
    level = stats["level"]

    if level == "healthy":
        return None

    parts = []

    if stats["swap_mb"] > 400:
        parts.append(f"swap at {stats['swap_mb']:.0f}MB")

    if stats["memory_pressure"] > 0.6:
        parts.append(f"memory pressure at {stats['memory_pressure']*100:.0f}%")

    if stats["cpu_percent"] > 75:
        parts.append(f"CPU at {stats['cpu_percent']:.0f}%")

    if not parts:
        return None

    detail = ", ".join(parts)

    if level == "critical":
        return f"🔴 System under stress ({score}/100): {detail}. Consider closing apps or unloading models."
    else:
        return f"🟡 System warming up ({score}/100): {detail}. Watching it."


def auto_heal(stats: Dict):
    """Auto-actions when system is critical."""
    if stats["level"] != "critical":
        return

    logger.warning("🚑 Auto-heal triggered — score: %d", stats["score"])

    # 1. Unload idle Ollama models
    try:
        import subprocess
        result = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines()[1:]:
            if line.strip():
                model = line.split()[0]
                subprocess.run(["ollama", "stop", model], timeout=5)
                logger.info("♻️  Auto-healed: unloaded %s", model)
                _broadcast(f"♻️ Auto-healed: unloaded {model} to free RAM.")
    except Exception as e:
        logger.debug("auto_heal ollama: %s", e)

    # 2. Clear response cache
    try:
        from core.response_cache import ResponseCache
        ResponseCache().clear()
        logger.info("🗑️  Response cache cleared")
    except Exception as e:
        logger.debug("auto_heal cache: %s", e)


# ── Background monitor loop ──────────────────────────────────────────────

_CHECK_INTERVAL = 120   # 2 minutes
_last_alerts: Dict = {}


def _monitor_loop():
    while True:
        try:
            stats = get_full_stats()
            now   = time.time()

            logger.debug(
                "🏥 Health: %d/100 (%s) | CPU:%d%% swap:%dMB pressure:%.2f",
                stats["score"], stats["level"],
                stats["cpu_percent"], stats["swap_mb"], stats["memory_pressure"]
            )

            msg = smart_message(stats)
            if msg:
                last = _last_alerts.get("health", 0)
                if now - last > 300:   # max once per 5 min
                    _broadcast(msg)
                    _last_alerts["health"] = now

            # Auto-heal on critical
            if stats["level"] == "critical":
                last_heal = _last_alerts.get("heal", 0)
                if now - last_heal > 600:  # max once per 10 min
                    auto_heal(stats)
                    _last_alerts["heal"] = now

            # Battery
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged and battery.percent < 20:
                last_bat = _last_alerts.get("battery", 0)
                if now - last_bat > 300:
                    _broadcast(f"🔋 Battery at {battery.percent:.0f}% — plug in soon.")
                    _last_alerts["battery"] = now

        except Exception as e:
            logger.debug("smart_guardian loop: %s", e)

        time.sleep(_CHECK_INTERVAL)


def start(broadcast_fn: Optional[Callable] = None):
    if broadcast_fn:
        set_broadcast(broadcast_fn)
    threading.Thread(target=_monitor_loop, daemon=True).start()
    logger.info("🛡️  SmartGuardian started (score-based, auto-heal enabled)")
