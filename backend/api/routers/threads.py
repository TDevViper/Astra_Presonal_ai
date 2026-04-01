"""
Conversation thread endpoints.
  POST   /threads/                    create thread
  GET    /threads/                    list my threads
  GET    /threads/{id}/messages       get messages
  POST   /threads/{id}/messages       add message + get AI reply
  PATCH  /threads/{id}                rename thread
  DELETE /threads/{id}                archive thread
  POST   /threads/{id}/fork           fork from message
"""

import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from auth.rbac import get_current_user, require_permission
from memory.threads_db import (
    init_db,
    create_thread,
    get_threads,
    get_thread,
    get_messages,
    add_message,
    rename_thread,
    archive_thread,
    fork_thread,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/threads", tags=["threads"])
init_db()


class CreateThread(BaseModel):
    title: str = "New Chat"


class RenameThread(BaseModel):
    title: str


class SendMessage(BaseModel):
    content: str
    use_ai: bool = True


class ForkThread(BaseModel):
    from_message_id: str
    title: str = "Forked Chat"


@router.post("/", status_code=201)
def create(body: CreateThread, current_user=Depends(require_permission("chat"))):
    thread = create_thread(str(uuid.uuid4()), current_user["id"], body.title)
    return thread


@router.get("/")
def list_threads(current_user=Depends(require_permission("chat"))):
    return get_threads(current_user["id"])


@router.get("/{thread_id}/messages")
def messages(thread_id: str, current_user=Depends(require_permission("chat"))):
    thread = get_thread(thread_id, current_user["id"])
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return get_messages(thread_id)


@router.post("/{thread_id}/messages")
def send(
    thread_id: str, body: SendMessage, current_user=Depends(require_permission("chat"))
):
    thread = get_thread(thread_id, current_user["id"])
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Store user message
    user_msg_id = str(uuid.uuid4())
    add_message(user_msg_id, thread_id, "user", body.content)

    reply = ""
    if body.use_ai:
        try:
            from core.brain_singleton import get_brain

            history = [
                {"role": m["role"], "content": m["content"]}
                for m in get_messages(thread_id, limit=20)[
                    :-1
                ]  # exclude just-added msg
            ]
            brain = get_brain()
            result = brain.process(body.content, history=history, session_id=thread_id)
            reply = result.get("reply", "")
        except Exception as e:
            logger.error("Brain error in thread %s: %s", thread_id, e)
            reply = f"[Error: {e}]"

        add_message(str(uuid.uuid4()), thread_id, "assistant", reply)

    return {"user_message_id": user_msg_id, "reply": reply}


@router.patch("/{thread_id}")
def rename(
    thread_id: str, body: RenameThread, current_user=Depends(require_permission("chat"))
):
    if not rename_thread(thread_id, current_user["id"], body.title):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": "Renamed"}


@router.delete("/{thread_id}")
def archive(thread_id: str, current_user=Depends(require_permission("chat"))):
    if not archive_thread(thread_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": "Archived"}


@router.post("/{thread_id}/fork", status_code=201)
def fork(
    thread_id: str, body: ForkThread, current_user=Depends(require_permission("chat"))
):
    thread = get_thread(thread_id, current_user["id"])
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    new_thread = fork_thread(
        new_id=str(uuid.uuid4()),
        source_thread_id=thread_id,
        user_id=current_user["id"],
        from_message_id=body.from_message_id,
        title=body.title,
    )
    return new_thread
