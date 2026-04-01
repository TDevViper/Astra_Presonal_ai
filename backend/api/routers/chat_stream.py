"""
api/routers/chat_stream.py — SSE streaming, fully async.
No ThreadPoolExecutor — uses native async Ollama client.
"""
import asyncio
import json
import logging
from fastapi import APIRouter, Depends, Request
from api.deps import require_api_key
from auth.rate_limiter import rate_limit
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_TOKEN_TIMEOUT = 30
_HEARTBEAT = 15


class ChatRequest(BaseModel):
    message: str = ""
    session_id: str = "default"
    history: list = []


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

    async def event_stream():
        from core.brain_singleton import get_brain
        from core.llm_backend import get_backend
        from personality.modes import get_temperature, get_token_budget

        brain = get_brain()
        full_reply = ""

        try:
            result = await asyncio.to_thread(
                brain.process,
                user_input,
                False,
                body.history or [],
                body.session_id,
            )

            if not result.get("__stream__"):
                reply = result.get("reply", "")
                for word in reply.split(" "):
                    if await request.is_disconnected():
                        break
                    yield f"data: {json.dumps({'type':'token','text':word+' '})}\n\n"
                    await asyncio.sleep(0)
                yield f"data: {json.dumps({'type':'done','full':reply,'confidence':result.get('confidence',0.6),'intent':result.get('intent',''),'agent':result.get('agent','')})}\n\n"
                return

            query_intent = result.get("query_intent", "casual")
            selected_model = result.get("selected_model", "phi3:mini")
            system_prompt = result.get("system_prompt", "")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.extend(body.history or [])
            messages.append({"role": "user", "content": user_input})

            backend = get_backend()
            options = {
                "temperature": get_temperature(),
                "num_predict": get_token_budget(query_intent),
            }

            async for token in backend.astream(messages, selected_model, options):
                if await request.is_disconnected():
                    logger.info("Client disconnected mid-stream")
                    break
                full_reply += token
                yield f"data: {json.dumps({'type':'token','text':token})}\n\n"

            yield f"data: {json.dumps({'type':'done','full':full_reply,'confidence':result.get('confidence',0.6),'intent':query_intent,'agent':f'ollama/{selected_model}'})}\n\n"

        except Exception as e:
            logger.error("chat_stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type':'error','message':'Stream failed'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
