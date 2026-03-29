# core/smart_guardian.py — v2: Context-aware scoring + trend tracking + auto-heal
import psutil
import subprocess
import platform
import logging
import threading
import time
from collections import deque
from typing import Dict, Optional, Callable, List

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
        return psutil.swap_memory().used / (1024 * 1024)
    except Exception:
        return 0.0


def get_memory_pressure() -> float:
    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(["memory_pressure"], text=True, timeout=3)
            for line in out.splitlines():
                if "System-wide memory free percentage" in line:
                    pct = float(line.split(":")[-1].strip().rstrip("%"))
                    return round(1.0 - pct / 100, 3)
        except Exception:
            pass
    swap_mb = get_swap_mb()
    if swap_mb < 100:  return 0.1
    if swap_mb < 300:  return 0.4
    if swap_mb < 600:  return 0.6
    return 0.85


def health_score(stats: Dict) -> int:
    """
    Context-aware scoring — swap is judged relative to memory pressure.
    High swap + low pressure = historical swap, minor penalty.
    High swap + high pressure = real stress, major penalty.
    """
    score    = 100
    swap_mb  = stats.get("swap_mb", 0)
    pressure = stats.get("memory_pressure", 0)
    ram_gb   = stats.get("ram_available_gb", 8)
    cpu      = stats.get("cpu_percent", 0)
    disk     = stats.get("disk_percent", 0)

    # ── Memory pressure (highest priority) ──
    if pressure > 0.8:   score -= 40
    elif pressure > 0.6: score -= 20
    elif pressure > 0.4: score -= 10

    # ── Swap — context-aware ──
    if swap_mb > 2000:
        # Is this active stress or historical?
        if pressure > 0.4:
            score -= 30   # active stress
        else:
            score -= 5    # historical — macOS keeps swap after pressure clears
    elif swap_mb > 800:
        score -= 15 if pressure > 0.4 else 3
    elif swap_mb > 300:
        score -= 8 if pressure > 0.4 else 1

    # ── RAM available ──
    if ram_gb < 1.0:   score -= 30
    elif ram_gb < 2.0: score -= 15
    elif ram_gb < 3.5: score -= 5

    # ── CPU ──
    if cpu > 90:   score -= 20
    elif cpu > 75: score -= 10
    elif cpu > 60: score -= 4

    # ── Disk ──
    if disk > 95:   score -= 10
    elif disk > 85: score -= 4

    return max(0, min(100, score))


def get_full_stats() -> Dict:
    vm    = psutil.virtual_memory()
    disk  = psutil.disk_usage("/")
    cpu   = psutil.cpu_percent(interval=0.5)
    swap  = get_swap_mb()
    press = get_memory_pressure()
    ram_gb = round(vm.available / 1024**3, 1)

    stats = {
        "cpu_percent":      cpu,
        "ram_percent":      round(vm.percent, 1),
        "ram_available_gb": ram_gb,
        "swap_mb":          round(swap, 0),
        "memory_pressure":  press,
        "disk_percent":     round(disk.percent, 1),
    }
    score = health_score(stats)
    level = "healthy" if score >= 80 else "warning" if score >= 55 else "critical"
    stats["score"] = score
    stats["level"] = level
    return stats


# ── Trend tracker ─────────────────────────────────────────────────────────

class TrendTracker:
    def __init__(self, window: int = 5):
        self._scores: deque = deque(maxlen=window)
        self._times:  deque = deque(maxlen=window)

    def add(self, score: int):
        self._scores.append(score)
        self._times.append(time.time())

    def trend(self) -> str:
        """Returns: improving | stable | degrading | unknown"""
        if len(self._scores) < 3:
            return "unknown"
        scores = list(self._scores)
        diffs  = [scores[i+1] - scores[i] for i in range(len(scores)-1)]
        avg    = sum(diffs) / len(diffs)
        if avg > 3:   return "improving"
        if avg < -3:  return "degrading"
        return "stable"

    def time_to_critical(self) -> Optional[int]:
        """Estimate minutes until score hits critical (< 55), or None."""
        if len(self._scores) < 3:
            return None
        scores = list(self._scores)
        list(self._times)
        diffs  = [scores[i+1] - scores[i] for i in range(len(scores)-1)]
        avg_per_check = sum(diffs) / len(diffs)
        if avg_per_check >= 0:
            return None  # not degrading
        current = scores[-1]
        checks_to_critical = (current - 55) / abs(avg_per_check)
        minutes = checks_to_critical * (_CHECK_INTERVAL / 60)
        return max(1, round(minutes))

    def summary(self) -> Dict:
        return {
            "trend":             self.trend(),
            "recent_scores":     list(self._scores),
            "time_to_critical":  self.time_to_critical(),
        }


_trend = TrendTracker(window=6)


def smart_message(stats: Dict, trend_summary: Dict) -> Optional[str]:
    score  = stats["score"]
    level  = stats["level"]
    trend  = trend_summary.get("trend", "unknown")
    ttc    = trend_summary.get("time_to_critical")

    if level == "healthy" and trend != "degrading":
        return None

    parts = []

    if stats["swap_mb"] > 2000 and stats["memory_pressure"] > 0.4:
        parts.append(f"swap {stats['swap_mb']:.0f}MB under active pressure")
    elif stats["swap_mb"] > 2000:
        parts.append(f"swap {stats['swap_mb']:.0f}MB (historical, low risk)")

    if stats["memory_pressure"] > 0.5:
        parts.append(f"memory pressure {stats['memory_pressure']*100:.0f}%")

    if stats["cpu_percent"] > 75:
        parts.append(f"CPU {stats['cpu_percent']:.0f}%")

    if stats["ram_available_gb"] < 2:
        parts.append(f"only {stats['ram_available_gb']}GB RAM free")

    if not parts:
        return None

    detail = ", ".join(parts)

    if level == "critical":
        msg = f"🔴 System critical ({score}/100): {detail}."
        if ttc:
            msg += " Trending critical."
        msg += " Auto-heal initiated."
        return msg

    if level == "warning":
        msg = f"🟡 System warning ({score}/100): {detail}."
        if trend == "degrading" and ttc:
            msg += f" Degrading — critical in ~{ttc} min."
        return msg

    if trend == "degrading" and ttc and ttc < 15:
        return f"📉 System degrading ({score}/100): {detail}. Critical in ~{ttc} min."

    return None


def auto_heal(stats: Dict):
    """Auto-actions when system hits critical."""
    if stats["level"] != "critical":
        return

    logger.warning("🚑 Auto-heal triggered — score: %d", stats["score"])
    healed = []

    # 1. Unload idle Ollama models
    try:
        result = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.splitlines()[1:]:
            if line.strip():
                model = line.split()[0]
                subprocess.run(["ollama", "stop", model], timeout=5)
                healed.append(f"unloaded {model}")
                logger.info("♻️  Unloaded: %s", model)
    except Exception as e:
        logger.debug("auto_heal ollama: %s", e)

    # 2. Clear response cache
    try:
        from core.response_cache import ResponseCache
        ResponseCache().clear()
        healed.append("cleared response cache")
        logger.info("🗑️  Cache cleared")
    except Exception as e:
        logger.debug("auto_heal cache: %s", e)

    # 3. Reduce context window temporarily
    try:
        import os
        os.environ["OLLAMA_NUM_CTX"] = "512"
        healed.append("reduced context to 512")
        logger.info("📉 Context window reduced to 512")
    except Exception as e:
        logger.debug("auto_heal ctx: %s", e)

    if healed:
        _broadcast(f"🚑 Auto-healed: {', '.join(healed)}.")


# ── Background monitor loop ───────────────────────────────────────────────

_CHECK_INTERVAL = 120
_last_alerts: Dict = {}


def _monitor_loop():
    logger.info("🛡️  SmartGuardian v2 monitor running")
    while True:
        try:
            stats  = get_full_stats()
            score  = stats["score"]
            _trend.add(score)
            trend_summary = _trend.summary()

            logger.debug(
                "🏥 score=%d (%s) trend=%s | CPU=%.0f%% RAM=%.1fGB swap=%.0fMB pressure=%.2f",
                score, stats["level"], trend_summary["trend"],
                stats["cpu_percent"], stats["ram_available_gb"],
                stats["swap_mb"], stats["memory_pressure"]
            )

            msg = smart_message(stats, trend_summary)
            now = time.time()
            if msg:
                last = _last_alerts.get("health", 0)
                if now - last > 300:
                    _broadcast(msg)
                    _last_alerts["health"] = now

            if stats["level"] == "critical":
                last_heal = _last_alerts.get("heal", 0)
                if now - last_heal > 600:
                    auto_heal(stats)
                    _last_alerts["heal"] = now

            # Battery
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged and battery.percent < 20:
                last_bat = _last_alerts.get("battery", 0)
                if now - last_bat > 300:
                    _broadcast(f"🔋 Battery {battery.percent:.0f}% — plug in soon.")
                    _last_alerts["battery"] = now

        except Exception as e:
            logger.debug("smart_guardian loop: %s", e)

        time.sleep(_CHECK_INTERVAL)


def get_trend_summary() -> Dict:
    return _trend.summary()


def start(broadcast_fn: Optional[Callable] = None):
    if broadcast_fn:
        set_broadcast(broadcast_fn)
    threading.Thread(target=_monitor_loop, daemon=True).start()
    logger.info("🛡️  SmartGuardian v2 started")
