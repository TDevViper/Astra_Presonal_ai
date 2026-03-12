import ollama
import json
import re
import logging
import threading
from typing import List, Dict

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """Extract entities and relationships from this text.
Return ONLY valid JSON, no markdown:
{{"entities": [{{"name": "...", "type": "person|place|tech|project|concept|tool|event"}}],
 "relations": [{{"from": "...", "to": "...", "relation": "..."}}]}}

Keep names short (1-3 words). Skip trivial words.
Text: {text}"""

_queue: List[Dict] = []
_lock  = threading.Lock()
_worker_running = False


def _worker_loop():
    global _worker_running
    import time
    while True:
        item = None
        with _lock:
            if _queue:
                item = _queue.pop(0)
        if item:
            _do_extract(item["text"], item["user_name"])
        else:
            time.sleep(2)
            with _lock:
                if not _queue:
                    _worker_running = False
                    return


def _ensure_worker():
    global _worker_running
    with _lock:
        if not _worker_running:
            _worker_running = True
            threading.Thread(target=_worker_loop, daemon=True).start()


def _do_extract(text: str, user_name: str = "User"):
    try:
        prompt   = EXTRACT_PROMPT.format(text=text[:600])
        response = ollama.chat(
            model="phi3:mini",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 250}
        )
        raw   = response["message"]["content"].strip()
        raw   = re.sub(r"```json|```", "", raw).strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return
        data  = json.loads(match.group())

        from knowledge.graph import add_entity, add_relation, save_graph
        added = 0
        for e in data.get("entities", []):
            name = e.get("name", "").strip()
            if name and len(name) > 1:
                add_entity(name, e.get("type", "concept"))
                added += 1
        for r in data.get("relations", []):
            frm = r.get("from", "").strip()
            to  = r.get("to", "").strip()
            rel = r.get("relation", "related_to").strip().replace(" ", "_")
            if frm and to and rel:
                add_relation(frm, rel, to)
                added += 1
        if added:
            save_graph()
            logger.info(f"Graph updated: +{added} items")
    except json.JSONDecodeError:
        pass
    except Exception as e:
        logger.debug(f"Extraction error: {e}")


def extract_and_store(text: str, user_name: str = "User"):
    if not text or len(text.strip()) < 20:
        return
    with _lock:
        _queue.append({"text": text, "user_name": user_name})
    _ensure_worker()


def extract_from_exchange(user_msg: str, assistant_msg: str, user_name: str = "User"):
    combined = f"User said: {user_msg}\nAssistant replied: {assistant_msg}"
    extract_and_store(combined, user_name)
