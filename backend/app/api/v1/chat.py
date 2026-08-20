"""Debate chat: history over REST, delivery over a WebSocket.

This is the resolution of blueprint conflict #3. ``docs/05-api-specification.md`` specified
a REST ``POST /room/{id}/message``; the repository has always carried a ``websocket/``
directory. Both are used, for the halves each is good at:

* **History is REST.** It stays readable when the socket is down, is cacheable by the
  client, and needs no socket to test.
* **Delivery is the socket.** REST alone cannot push the other side's message without
  polling, and two seconds of latency that is invisible in a matchmaking queue makes a chat
  feel broken.

A message is persisted *before* it is broadcast, and the sender is echoed rather than
rendering its own copy, so both windows show what the database holds instead of optimistic
state that can disagree with it.
"""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import ClerkTokenVerifier, get_token_verifier
from app.auth.dependencies import CurrentUser
from app.core.config import Settings, get_settings
from app.core.errors import AppError, AuthenticationError
from app.db.session import SessionScope, get_db, get_session_scope
from app.models.user import User
from app.schemas.chat import (
    ErrorFrame,
    MessageFrame,
    MessageList,
    ReadyFrame,
    SendMessageFrame,
    client_frame_adapter,
)
from app.services import chat as chat_service
from app.websocket.auth import authenticate_socket, origin_allowed
from app.websocket.protocol import CLOSE_FORBIDDEN, close_code_for
from app.websocket.registry import chat_registry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Scope = Annotated[SessionScope, Depends(get_session_scope)]
Verifier = Annotated[ClerkTokenVerifier, Depends(get_token_verifier)]


@router.get(
    "/rooms/{room_id}/messages",
    response_model=MessageList,
    summary="Get a debate's chat history",
    responses={
        401: {"description": "Missing or invalid Clerk session token."},
        403: {"description": "You are not a participant in this debate."},
        404: {"description": "No such room."},
    },
)
async def get_messages(room_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> MessageList:
    """Every message in the room, oldest first.

    Readable after the debate ends — a reconnecting client and the results screen both
    need the transcript of a room that has closed.
    """
    messages = await chat_service.list_history(db, room_id, current_user)
    return MessageList(messages=messages)


@router.websocket("/rooms/{room_id}/chat")
async def chat_socket(
    websocket: WebSocket,
    room_id: uuid.UUID,
    verifier: Verifier,
    scope: Scope,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Live chat for one debate.

    Protocol: the client sends ``{"type": "auth", "token": …}`` first and nothing else is
    accepted until it does; on success the server replies ``{"type": "ready", …}`` and the
    client loads history. Thereafter ``{"type": "message", "content": …}`` goes up, and
    ``{"type": "message", "message": {…}}`` comes back down to *both* debaters.

    Failures before ``ready`` close the connection with a code from
    ``app.websocket.protocol``. Failures after it are sent as an error frame and the socket
    stays open.
    """
    if not origin_allowed(websocket, settings):
        # Refuse the handshake outright rather than accepting and closing: there is nothing
        # to say to a page we do not serve.
        await websocket.close(code=CLOSE_FORBIDDEN)
        return

    await websocket.accept()

    try:
        user = await authenticate_socket(websocket, verifier, scope)
        # Proves the room exists and that this user is one of its two debaters, using the
        # same check as GET /rooms/{id}. An ended room is still joinable — the transcript
        # remains readable — but post_message refuses to add to it.
        async with scope() as db:
            await chat_service.list_history(db, room_id, user)
    except WebSocketDisconnect:
        return
    except AppError as error:
        await websocket.close(code=close_code_for(error), reason=error.message)
        return

    await chat_registry.add(room_id, websocket)
    logger.info(
        "Chat socket connected",
        extra={"room_id": str(room_id), "user_id": str(user.id)},
    )

    try:
        ready = ReadyFrame(room_id=room_id, user_id=user.id)
        await websocket.send_json(ready.model_dump(by_alias=True, mode="json"))
        await _receive_loop(websocket, room_id=room_id, user=user, scope=scope)
    except WebSocketDisconnect:
        pass
    finally:
        # Unconditional: an exception mid-loop must not leave a dead socket in the registry
        # for every later broadcast to try and fail on.
        await chat_registry.discard(room_id, websocket)
        logger.info("Chat socket disconnected", extra={"room_id": str(room_id)})


async def _receive_loop(
    websocket: WebSocket, *, room_id: uuid.UUID, user: User, scope: SessionScope
) -> None:
    """Persist and broadcast messages until the client goes away."""
    while True:
        try:
            raw = await websocket.receive_json()
        except (ValueError, TypeError):
            await _send_error(websocket, "validation_error", "Message was not valid JSON.")
            continue

        try:
            frame = client_frame_adapter.validate_python(raw)
        except Exception:  # noqa: BLE001 - pydantic's ValidationError, reported to the client
            await _send_error(websocket, "validation_error", "Message must be 1–2000 characters.")
            continue

        if not isinstance(frame, SendMessageFrame):
            # A second auth frame, most likely. Authentication already happened and is not
            # repeatable on an open socket.
            await _send_error(websocket, "validation_error", "Unexpected frame.")
            continue

        try:
            async with scope() as db:
                message = await chat_service.post_message(db, room_id, user, frame.content)
        except AuthenticationError:
            # Cannot happen after a successful handshake, but if it ever does the socket is
            # no longer trustworthy.
            raise
        except AppError as error:
            # The debate ended mid-conversation, say. The client is told and stays connected
            # so it can keep reading.
            await _send_error(websocket, error.code, error.message)
            continue

        await chat_registry.broadcast(
            room_id, MessageFrame(message=message).model_dump(by_alias=True, mode="json")
        )


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json(
        ErrorFrame(code=code, message=message).model_dump(by_alias=True, mode="json")
    )
