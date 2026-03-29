# api/ws_stream.py — WebSocket broadcast stub
# Flask-sock removed; broadcast is a no-op until WebSocket is ported to FastAPI
import logging
logger = logging.getLogger(__name__)

def broadcast(message: str) -> None:
    logger.debug("ws_stream broadcast (stub): %s", str(message)[:80])
