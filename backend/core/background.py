"""
core/background.py — Managed async background tasks for ASTRA.
Each task runs in its own asyncio loop with isolated error handling.
A crash in one task never affects the others.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


async def _run_threaded(name: str, start_fn, *args, **kwargs):
    """Run a blocking start_fn in a thread, log errors, never crash the app."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: start_fn(*args, **kwargs))
        logger.info("✅ %s started", name)
    except Exception as e:
        logger.warning("⚠️  %s failed to start: %s", name, e)


async def _poll(name: str, fn, interval: int):
    """Run fn() every interval seconds. Isolated — exceptions don't stop the loop."""
    logger.info("🔄 %s polling every %ds", name, interval)
    while True:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, fn)
        except asyncio.CancelledError:
            logger.info("🛑 %s stopped", name)
            return
        except Exception as e:
            logger.warning("⚠️  %s error: %s", name, e)
        await asyncio.sleep(interval)


async def start_all(broadcast_fn) -> list:
    """
    Start all background tasks. Returns list of asyncio.Task objects
    so lifespan can cancel them on shutdown.
    """
    tasks = []

    # ── Broadcast wiring ─────────────────────────────────────────────────────
    try:
        from core.proactive import set_broadcast as _pb
        from core.smart_guardian import set_broadcast as _gb
        _pb(broadcast_fn)
        _gb(broadcast_fn)
    except Exception as e:
        logger.warning("Broadcast wiring failed: %s", e)

    # ── TTS worker — moved here from module-level ───────────────────────────────
    try:
        from core.llm_engine import start_tts_worker
        start_tts_worker()
    except Exception as e:
        logger.warning("TTS worker failed to start: %s", e)

    # ── Ollama auto-unload — moved here from module-level ───────────────────────
    try:
        from core.model_manager import start_auto_unload
        start_auto_unload()
    except Exception as e:
        logger.warning("Ollama auto-unload failed to start: %s", e)

    # ── SmartGuardian — runs its own thread internally ────────────────────────
    try:
        from core.smart_guardian import _monitor_loop
        tasks.append(asyncio.create_task(
            _poll("SmartGuardian", _monitor_loop_once, 120),
            name="smart_guardian"
        ))
    except Exception as e:
        logger.warning("SmartGuardian task failed: %s", e)

    # ── Proactive monitor ─────────────────────────────────────────────────────
    try:
        from core.proactive import _check_system, _check_tasks
        last_alerts: dict = {}
        tasks.append(asyncio.create_task(
            _poll("ProactiveMonitor",
                  lambda: (_check_system(last_alerts), _check_tasks(last_alerts)),
                  120),
            name="proactive_monitor"
        ))
    except Exception as e:
        logger.warning("ProactiveMonitor task failed: %s", e)

    # ── Plugin watcher ────────────────────────────────────────────────────────
    try:
        from tools.plugin_watcher import start as _start_plugins
        tasks.append(asyncio.create_task(
            _run_threaded("PluginWatcher", _start_plugins),
            name="plugin_watcher"
        ))
    except Exception as e:
        logger.warning("PluginWatcher task failed: %s", e)

    # ── GPU health ────────────────────────────────────────────────────────────
    try:
        from core.gpu_health import _check_once
        tasks.append(asyncio.create_task(
            _poll("GpuHealth", _check_once, 15),
            name="gpu_health"
        ))
    except Exception as e:
        logger.warning("GpuHealth task failed: %s", e)

    # ── RAG doc watcher ───────────────────────────────────────────────────────
    try:
        from rag.watcher import _scan_and_ingest
        tasks.append(asyncio.create_task(
            _poll("DocWatcher", _scan_and_ingest, 30),
            name="doc_watcher"
        ))
    except Exception as e:
        logger.warning("DocWatcher task failed: %s", e)

    logger.info("🚀 %d background tasks started", len(tasks))
    return tasks


async def stop_all(tasks: list):
    """Cancel all background tasks and wait for them to finish."""
    for t in tasks:
        if not t.done():
            t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("🛑 All background tasks stopped")


# ── SmartGuardian single-tick helper (avoids re-entering its own while loop) ──
def _monitor_loop_once():
    """Run one tick of SmartGuardian logic (used by _poll above)."""
    import time
    from core.smart_guardian import (
        get_full_stats, _trend, smart_message,
        auto_heal, _last_alerts, _broadcast
    )
    import psutil

    stats         = get_full_stats()
    score         = stats["score"]
    _trend.add(score)
    trend_summary = _trend.summary()

    msg = smart_message(stats, trend_summary)
    now = time.time()
    if msg and now - _last_alerts.get("health", 0) > 300:
        _broadcast(msg)
        _last_alerts["health"] = now

    if stats["level"] == "critical":
        last_heal = _last_alerts.get("heal", 0)
        if now - last_heal > 600:
            auto_heal(stats)
            _last_alerts["heal"] = now

    battery = psutil.sensors_battery()
    if battery and not battery.power_plugged and battery.percent < 20:
        if now - _last_alerts.get("battery", 0) > 300:
            _broadcast(f"🔋 Battery {battery.percent:.0f}% — plug in soon.")
            _last_alerts["battery"] = now
