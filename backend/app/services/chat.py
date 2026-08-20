"""Debate chat rules.

Two operations — read a room's history, and post a message — and both answer the same
question first: *is this caller allowed in this room?* That check is not reimplemented here.
``to_room_read()`` in ``app.services.match`` already raises for a non-participant and is
what guards ``GET /rooms/{id}``; reusing it means the socket and the REST route cannot
drift apart into disagreeing about who may see a debate.

Delivery is the WebSocket layer's job (``app/websocket/``). This module only decides what
is allowed and what is stored, so it stays testable without a socket.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.user import User
from app.repositories import match as match_repo
from app.repositories import message as message_repo
from app.schemas.chat import MessageRead
from app.services.match import to_room_read

logger = logging.getLogger(__name__)


async def _get_room_for_participant(db: AsyncSession, room_id: uuid.UUID, user: User):
    """Load a room, refusing unknown ids and anyone who is not one of its two debaters."""
    room = await match_repo.get_room(db, room_id)
    if room is None:
        raise NotFoundError("Debate room not found.")
    # Raises PermissionDeniedError for outsiders. The return value is discarded — this is
    # called for the check, and reusing it is the point.
    to_room_read(room, user.id)
    return room


async def list_history(db: AsyncSession, room_id: uuid.UUID, user: User) -> list[MessageRead]:
    """Every message in a room, oldest first.

    Deliberately readable in an ended debate: the results screen and a reconnecting client
    both need the transcript after the room closes.
    """
    await _get_room_for_participant(db, room_id, user)
    messages = await message_repo.list_messages(db, room_id)
    return [MessageRead.model_validate(message) for message in messages]


async def post_message(
    db: AsyncSession, room_id: uuid.UUID, user: User, content: str
) -> MessageRead:
    """Persist one message from a participant, returning it as it was stored.

    Returning the stored row rather than the submitted text is what lets the socket echo
    to the sender: both windows then render the same server-assigned id and timestamp.
    """
    room = await _get_room_for_participant(db, room_id, user)
    if room.ended_at is not None:
        raise ConflictError("This debate has ended.")

    message = await message_repo.add_message(
        db, room_id=room_id, sender_id=user.id, content=content
    )
    await db.commit()

    logger.info(
        "Chat message stored",
        extra={"room_id": str(room_id), "message_id": str(message.id)},
    )
    return MessageRead.model_validate(message)
