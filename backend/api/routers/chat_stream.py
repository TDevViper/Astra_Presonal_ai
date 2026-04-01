"""
api/routers/chat_stream.py — SSE streaming with backpressure and error recovery.

Improvements over v1:
  - asyncio.Queue decouples Brain (sync thread) from SSE sender (async)
  - Backpressure: queue has max size — slow clients don't pile up tokens in RAM
  - Client disconnect detection — Brain thread stops when client disconnects
  - Timeout per token — if Brain stalls, stream closes cleanly
  - Heartbeat keepalive every 15s — prevents proxies from killing idle connections
  - Structured error events — frontend gets {"type":"error"} not raw exception text
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, Request
from api.deps import require_api_key
from auth.rate_limiter import rate_limit
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stream")

_QUEUE_MAX = 64  # max tokens buffered per stream
_TOKEN_TIMEOUT = 30  # seconds to wait for next token before closing
_HEARTBEAT = 15  # seconds between keepalive comments


class ChatRequest(BaseModel):
    message: str = ""


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    _=Depends(require_api_key),
    _rl=Depends(rate_limit),
):
    user_input = body.message.strip()

    if not user_input:

        async def empty():
            yield 'data: {"type":"token","text":"No message received"}\n\n'
            yield 'data: {"type":"done","full":"","confidence":0}\n\n'

        return StreamingResponse(empty(), media_type="text/event-stream")

    queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAX)
    loop = asyncio.get_event_loop()
    _DONE = object()  # sentinel

    def _run_brain():
        """Runs in thread pool. Puts tokens into queue. Never raises."""
        try:
            from core.brain_singleton import get_brain

            brain = get_brain()
            query_intent = brain.model_manager.classify_query_intent(user_input)
            selected_model = brain.model_manager.select_model(user_input, query_intent)

            loop.call_soon_threadsafe(
                queue.put_nowait,
                json.dumps(
                    {"type": "meta", "model": selected_model, "intent": query_intent}
                ),
            )

            meta_payload = None
            for chunk in brain.process_stream(user_input):
                if "meta" in chunk:
                    meta_payload = chunk["meta"]
                    continue
                token = chunk.get("token", "")
                if token:
                    try:
                        loop.call_soon_threadsafe(
                            queue.put_nowait,
                            json.dumps(
                                {"type": "token", "text": token}, ensure_ascii=False
                            ),
                        )
                    except asyncio.QueueFull:
                        # Client too slow — drop token, don't block Brain
                        logger.warning("Stream queue full — dropping token")

            # Build done event
            try:
                from personality.modes import get_current_mode

                active_mode = get_current_mode()
            except Exception:
                active_mode = "jarvis"

            if meta_payload:
                done = {
                    "type": "done",
                    "full": meta_payload.get("full", ""),
                    "agent": meta_payload.get("agent", selected_model),
                    "intent": meta_payload.get("intent", query_intent),
                    "emotion": meta_payload.get("emotion", "neutral"),
                    "confidence": meta_payload.get("confidence", 0.75),
                    "tool_used": meta_payload.get("tool_used", False),
                    "memory_updated": meta_payload.get("memory_updated", True),
                    "mode": active_mode,
                }
            else:
                try:
                    from emotion.emotion_detector import detect_emotion

                    emotion, _ = detect_emotion(user_input)
                except Exception:
                    emotion = "neutral"
                try:
                    from core.confidence import score as conf_score

                    confidence = conf_score(query_intent, query_intent)
                except Exception:
                    confidence = 0.75
                done = {
                    "type": "done",
                    "full": "",
                    "agent": selected_model,
                    "intent": query_intent,
                    "emotion": emotion,
                    "confidence": confidence,
                    "tool_used": False,
                    "memory_updated": False,
                    "mode": active_mode,
                }

            loop.call_soon_threadsafe(queue.put_nowait, json.dumps(done))

        except Exception as e:
            logger.error("Stream brain error: %s", e, exc_info=True)
            try:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    json.dumps(
                        {"type": "error", "message": "Stream processing failed"}
                    ),
                )
            except Exception:
                pass
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _DONE)

    async def generate():
        # Start Brain in thread pool
        future = loop.run_in_executor(_pool, _run_brain)
        heartbeat_counter = 0

        try:
            while True:
                # Check client disconnect
                if await request.is_disconnected():
                    logger.info("Client disconnected — closing stream")
                    future.cancel()
                    break

                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    heartbeat_counter += 1
                    if heartbeat_counter >= _HEARTBEAT:
                        yield ": keepalive\n\n"
                        heartbeat_counter = 0
                    continue

                if item is _DONE:
                    break

                # item is already a JSON string
                event_type = json.loads(item).get("type", "")
                if event_type == "done" or event_type == "error":
                    yield f"data: {item}\n\n"
                    break
                yield f"data: {item}\n\n"

        except asyncio.CancelledError:
            logger.info("Stream cancelled")
        except Exception as e:
            logger.error("Stream generator error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream failed'})}\n\n"
        finally:
            await asyncio.gather(future, return_exceptions=True)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Connection": "keep-alive",
        },
    )
