# api/ws_stream.py
# WebSocket streaming — full Brain pipeline, real-time token delivery
import json, threading, logging
from flask_sock import Sock

logger = logging.getLogger(__name__)

sock = Sock()

# ── Connected clients for proactive broadcasts ────────────────────────────
_connected_clients: list = []
_lock = threading.Lock()


def broadcast(message: str):
    """Push proactive alerts to all connected WebSocket clients."""
    with _lock:
        dead = []
        for ws in _connected_clients:
            try:
                ws.send(json.dumps({"type": "proactive", "data": message}))
            except Exception:
                dead.append(ws)
        for ws in dead:
            _connected_clients.remove(ws)


# ── Main WebSocket handler ────────────────────────────────────────────────

@sock.route('/ws')
def websocket_handler(ws):
    """
    Full-duplex WebSocket endpoint.

    Client sends:
        {"type": "chat", "text": "...", "image": "<base64 or null>"}
        {"type": "ping"}

    Server sends:
        {"type": "connected"}
        {"type": "token",  "data": "..."}
        {"type": "meta",   "data": {...}}
        {"type": "done"}
        {"type": "error",  "data": "..."}
        {"type": "proactive", "data": "..."}
        {"type": "pong"}
    """
    with _lock:
        _connected_clients.append(ws)

    # Send connection acknowledgement
    try:
        ws.send(json.dumps({"type": "connected", "data": "ASTRA WebSocket ready"}))
    except Exception as e:
        logger.warning("WS send connected failed: %s", e)

    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                ws.send(json.dumps({"type": "error", "data": "Invalid JSON"}))
                continue

            msg_type = msg.get("type", "chat")

            # ── Ping/pong ─────────────────────────────────────────────────
            if msg_type == "ping":
                ws.send(json.dumps({"type": "pong"}))
                continue

            # ── Chat ──────────────────────────────────────────────────────
            if msg_type == "chat":
                user_input = msg.get("text", "").strip()
                image_b64  = msg.get("image")

                if not user_input:
                    ws.send(json.dumps({"type": "error", "data": "Empty message"}))
                    continue

                if len(user_input) > 4000:
                    ws.send(json.dumps({"type": "error",
                                        "data": "Message too long (max 4000 chars)"}))
                    continue

                _handle_chat(ws, user_input, image_b64)
                continue

            ws.send(json.dumps({"type": "error", "data": f"Unknown type: {msg_type}"}))

    except Exception as e:
        logger.warning("WebSocket connection closed: %s", e)
    finally:
        with _lock:
            if ws in _connected_clients:
                _connected_clients.remove(ws)


def _handle_chat(ws, user_input: str, image_b64=None):
    """Stream Brain.process_stream() tokens over WebSocket."""
    from core.brain_singleton import get_brain

    brain = get_brain()

    try:
        # If image attached — use non-streaming vision path
        if image_b64:
            result = brain.process(user_input, vision_mode=True)
            ws.send(json.dumps({"type": "token", "data": result.get("reply", "")}))
            ws.send(json.dumps({
                "type": "meta",
                "data": {
                    "full":       result.get("reply", ""),
                    "intent":     result.get("intent", "vision"),
                    "agent":      result.get("agent", "llava"),
                    "emotion":    result.get("emotion", "neutral"),
                    "confidence": result.get("confidence", 0.8),
                    "tool_used":  result.get("tool_used", False),
                }
            }))
            ws.send(json.dumps({"type": "done"}))
            return

        # Text — full streaming pipeline
        done_sent = False
        for item in brain.process_stream(user_input):
            if "token" in item:
                ws.send(json.dumps({"type": "token", "data": item["token"]}))
            elif "meta" in item:
                ws.send(json.dumps({"type": "meta", "data": item["meta"]}))
                ws.send(json.dumps({"type": "done"}))
                done_sent = True
        if not done_sent:
            ws.send(json.dumps({"type": "done"}))

    except Exception as e:
        logger.error("WS _handle_chat error: %s", e, exc_info=True)
        try:
            ws.send(json.dumps({"type": "error", "data": "Something went wrong"}))
            ws.send(json.dumps({"type": "done"}))
        except Exception:
            pass
