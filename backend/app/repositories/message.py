"""Chat message persistence.

Two operations, which is all chat needs: append one, and read a room's history oldest
first. The ``(room_id, created_at)`` index on ``messages`` exists for exactly that read.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message

# How much history one request returns. A debate is a single sitting, so this is far more
# than a room will realistically hold; pagination can wait until something needs it.
HISTORY_LIMIT = 500


async def add_message(
    db: AsyncSession, *, room_id: uuid.UUID, sender_id: uuid.UUID, content: str
) -> Message:
    """Append a message. The caller commits.

    ``created_at`` is set explicitly to ``clock_timestamp()`` rather than left to the
    column's ``now()`` default. In Postgres ``now()`` is the *transaction* start time, so
    two messages written inside one transaction get byte-identical timestamps and the
    ordered read below has nothing to separate them — it falls through to the random UUID
    tiebreak and returns them shuffled. ``clock_timestamp()`` is the real clock at the
    moment of the INSERT, so it advances within a transaction. This needs no migration:
    the column default remains as the fallback for any other writer.
    """
    message = Message(
        room_id=room_id,
        sender_id=sender_id,
        content=content,
        created_at=func.clock_timestamp(),
    )
    db.add(message)
    await db.flush()
    # The value above is a SQL expression until the database evaluates it; without this the
    # returned object carries the expression rather than a datetime, and serialising it fails.
    await db.refresh(message)
    return message


async def list_messages(
    db: AsyncSession, room_id: uuid.UUID, *, limit: int = HISTORY_LIMIT
) -> Sequence[Message]:
    """A room's messages, oldest first.

    Ordered by ``(created_at, id)``: two messages can share a timestamp at the database's
    resolution, and an unstable tail would make the client's ordering flicker between
    loads. The id is the tiebreak because it is unique and already indexed as the key.
    """
    result = await db.scalars(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at, Message.id)
        .limit(limit)
    )
    return result.all()
