"""Fact-check persistence and the counts the rate limits are derived from.

The counts are queries against ``fact_checks`` itself rather than an in-memory tally. That
is the Phase 4 lesson applied without having to relearn it: a per-process counter is wrong
the moment the API runs more than one worker, and it also forgets everything on restart —
which, for a limit whose job is to protect a *daily* quota, means a redeploy hands out a
fresh budget. The ``room_id`` index already exists, and these are counting queries over a
small table.
"""

import uuid
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fact_check import FactCheck, FactCheckVerdict


async def add_fact_check(
    db: AsyncSession,
    *,
    room_id: uuid.UUID,
    requester_id: uuid.UUID,
    claim: str,
    verdict: FactCheckVerdict,
    explanation: str,
    sources: list[dict[str, Any]],
) -> FactCheck:
    """Record one result. The caller commits."""
    fact_check = FactCheck(
        room_id=room_id,
        requester_id=requester_id,
        claim=claim,
        verdict=verdict,
        explanation=explanation,
        sources=sources,
        # Same reasoning as messages: Postgres `now()` is the transaction start time, so
        # rows written in one transaction share a timestamp and an ordered read falls
        # through to the random-UUID tiebreak. See app/repositories/message.py.
        created_at=func.clock_timestamp(),
    )
    db.add(fact_check)
    await db.flush()
    await db.refresh(fact_check)
    return fact_check


async def list_for_room(db: AsyncSession, room_id: uuid.UUID) -> Sequence[FactCheck]:
    """Every fact-check in a room, oldest first."""
    result = await db.scalars(
        select(FactCheck)
        .where(FactCheck.room_id == room_id)
        .order_by(FactCheck.created_at, FactCheck.id)
    )
    return result.all()


async def count_for_room_since(db: AsyncSession, room_id: uuid.UUID, window: timedelta) -> int:
    """How many fact-checks this room has run recently."""
    cutoff = func.now() - window
    return (
        await db.scalar(
            select(func.count())
            .select_from(FactCheck)
            .where(FactCheck.room_id == room_id, FactCheck.created_at >= cutoff)
        )
    ) or 0


async def count_since(db: AsyncSession, window: timedelta) -> int:
    """How many fact-checks the whole deployment has run recently.

    This is the one that protects the shared free-tier quota — a per-room limit cannot,
    because rooms do not know about each other.
    """
    return (
        await db.scalar(
            select(func.count())
            .select_from(FactCheck)
            .where(FactCheck.created_at >= func.now() - window)
        )
    ) or 0
