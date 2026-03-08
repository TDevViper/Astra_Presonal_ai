from flask_sock import Sock
import json, threading

sock = Sock()

_connected_clients = []
_lock = threading.Lock()

def broadcast(message: str):
    with _lock:
        dead = []
        for ws in _connected_clients:
            try:
                ws.send(json.dumps({"type": "proactive", "data": message}))
            except Exception:
                dead.append(ws)
        for ws in dead:
            _connected_clients.remove(ws)

@sock.route('/ws')
def websocket_stream(ws):
    with _lock:
        _connected_clients.append(ws)
    try:
        while True:
            data = ws.receive()
            if not data:
                break
            msg        = json.loads(data)
            user_input = msg.get("text", "")
            image_b64  = msg.get("image")
            for token in _stream_ollama(user_input, image_b64):
                ws.send(json.dumps({"type": "token", "data": token}))
            ws.send(json.dumps({"type": "done"}))
    except Exception:
        pass
    finally:
        with _lock:
            if ws in _connected_clients:
                _connected_clients.remove(ws)

def _stream_ollama(text, image=None):
    import ollama
    client   = ollama.Client()
    messages = [{"role": "user", "content": text}]
    for chunk in client.chat(model="mistral", messages=messages, stream=True):
        yield chunk['message']['content']
