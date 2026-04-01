# tools/plugin_watcher.py
# Hot-reload plugin system — drop a .py file in plugins/ and ASTRA
# picks it up immediately without restart
import os
import time
import threading
import importlib
import logging

logger = logging.getLogger(__name__)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(_BACKEND_DIR, "plugins")

_watched: dict = {}  # filepath → mtime
_running = False


def _load_plugin(filepath: str) -> bool:
    fname = os.path.basename(filepath)
    mod_name = f"plugins.{fname[:-3]}"
    try:
        if mod_name in __import__("sys").modules:
            mod = __import__("sys").modules[mod_name]
            importlib.reload(mod)
            logger.info("♻️  Reloaded plugin: %s", fname)
        else:
            spec = importlib.util.spec_from_file_location(mod_name, filepath)
            mod = importlib.util.module_from_spec(spec)
            __import__("sys").modules[mod_name] = mod
            spec.loader.exec_module(mod)
            logger.info("🔌 Loaded plugin: %s", fname)
        return True
    except Exception as e:
        logger.error("Plugin load failed (%s): %s", fname, e)
        return False


def _scan():
    if not os.path.isdir(PLUGINS_DIR):
        return
    for fname in os.listdir(PLUGINS_DIR):
        if fname.startswith("_") or not fname.endswith(".py"):
            continue
        fpath = os.path.join(PLUGINS_DIR, fname)
        mtime = os.path.getmtime(fpath)
        if fpath not in _watched or _watched[fpath] != mtime:
            _load_plugin(fpath)
            _watched[fpath] = mtime


def _watch_loop():
    while _running:
        try:
            _scan()
        except Exception as e:
            logger.debug("plugin_watcher scan error: %s", e)
        time.sleep(3)


def start():
    global _running
    os.makedirs(PLUGINS_DIR, exist_ok=True)
    # Write a README so the user knows what to do
    readme = os.path.join(PLUGINS_DIR, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w") as f:
            f.write("""# ASTRA Plugins

Drop any .py file here and ASTRA hot-loads it within 3 seconds.

## Example plugin
```python
After saving, ASTRA's ReAct agent can immediately use:
  Action: weather(London)
""")
    _running = True
    _scan()  # load existing plugins immediately
    t = threading.Thread(target=_watch_loop, daemon=True, name="plugin-watcher")
    t.start()
    logger.info("🔌 Plugin watcher started (dir=%s)", PLUGINS_DIR)


def stop():
    global _running
    _running = False


def list_plugins() -> list:
    return [os.path.basename(f) for f in _watched]
