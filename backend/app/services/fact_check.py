"""The on-demand AI fact-check.

This is the feature the whole product exists to evaluate, so its rules are worth stating
plainly:

* **Only the claim crosses the boundary.** Not the room, not the opponent, not the
  transcript. That is the isolation property ``docs/03-system-architecture.md`` draws the AI
  service as a separate box to guarantee.
* **A verdict is only shown when a trusted source backs it.** Sources are filtered to the
  allowlist in ``app/core/sources.py``, and a result with nothing left is downgraded to
  ``unverified``. A verdict the debaters cannot check is worse than no verdict.
* **"Could not check" is never recorded as "checked and unresolved."** Provider failures
  raise; nothing is persisted. See ``app/ai/base.py`` for why that distinction is the most
  important one in this phase.

Delivery is the caller's job — the endpoint broadcasts over the chat socket — so this module
stays testable without a socket, exactly like ``app/services/chat.py``.
"""

import logging
import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import FactCheckProvider, ProviderResult, ProviderSource
from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, RateLimitError
from app.core.sources import is_trusted_domain, source_domain
from app.models.fact_check import FactCheckVerdict
from app.models.user import User
from app.repositories import fact_check as fact_check_repo
from app.repositories import match as match_repo
from app.schemas.fact_check import FactCheckRead
from app.services.match import to_room_read

logger = logging.getLogger(__name__)

ROOM_WINDOW = timedelta(hours=1)
BUDGET_WINDOW = timedelta(days=1)


async def _get_room_for_participant(db: AsyncSession, room_id: uuid.UUID, user: User):
    """Load a room, refusing unknown ids and anyone who is not one of its two debaters."""
    room = await match_repo.get_room(db, room_id)
    if room is None:
        raise NotFoundError("Debate room not found.")
    # Raises PermissionDeniedError for outsiders. Same guard as GET /rooms/{id} and the chat
    # socket, so the three cannot drift apart about who may see a debate.
    to_room_read(room, user.id)
    return room


def _trusted_sources(sources: list[ProviderSource]) -> list[dict[str, str]]:
    """Keep only citations from the allowlist, in the provider's order.

    Judged on ``domain`` where the provider supplies one, because Gemini's grounding
    metadata returns ``url`` as a redirect link rather than the publisher's own address —
    filtering on the URL would discard every citation. Falls back to the URL's host for
    providers whose URLs are already the publisher's.
    """
    kept: list[dict[str, str]] = []
    for source in sources:
        host = source.domain or source_domain(source.url)
        if not is_trusted_domain(host):
            continue
        kept.append({"title": source.title, "url": source.url})
    return kept


def _apply_trust_filter(
    result: ProviderResult,
) -> tuple[FactCheckVerdict, str, list[dict[str, str]]]:
    """Reduce a provider's answer to what may be shown.

    When nothing survives the filter, the verdict is downgraded to ``unverified`` however
    confident the model was. The model may well be right — but the debaters have no way to
    check it, and an unbacked verdict delivered with authority into an argument is the
    failure mode this feature most needs to avoid.
    """
    sources = _trusted_sources(result.sources)
    if sources or result.verdict == FactCheckVerdict.UNVERIFIED:
        return result.verdict, result.explanation, sources

    logger.info(
        "Downgrading a verdict with no trusted sources",
        extra={"original_verdict": result.verdict.value},
    )
    return (
        FactCheckVerdict.UNVERIFIED,
        "No trusted source could be found to support or refute this claim.",
        [],
    )


async def _enforce_limits(db: AsyncSession, room_id: uuid.UUID, settings: Settings) -> None:
    """Two limits, because they defend against different things.

    The per-room limit stops one debate hammering the button. It cannot protect the daily
    free-tier quota, though, because rooms do not know about each other — thirty rooms at
    ten checks each exhausts a 250/day tier and every later fact-check fails for everyone.
    The budget check is what defends that, and it is deliberately set below the real quota
    so the refusal is ours and legible rather than the provider's 429.
    """
    used_today = await fact_check_repo.count_since(db, BUDGET_WINDOW)
    if used_today >= settings.fact_check_daily_budget:
        logger.warning("Daily fact-check budget exhausted", extra={"used": used_today})
        raise RateLimitError(
            "The fact-check service has reached its daily limit. It resets within 24 hours."
        )

    used_here = await fact_check_repo.count_for_room_since(db, room_id, ROOM_WINDOW)
    if used_here >= settings.fact_check_rate_limit_per_hour:
        raise RateLimitError(
            f"This debate has used its {settings.fact_check_rate_limit_per_hour} fact-checks "
            "for the hour."
        )


async def list_for_room(db: AsyncSession, room_id: uuid.UUID, user: User) -> list[FactCheckRead]:
    """Every fact-check in a room, oldest first.

    A separate endpoint from chat history rather than a row in ``messages``, because
    ``messages.sender_id`` is ``NOT NULL`` and references ``users`` — a system-authored
    message has no author to point at. Keeping them apart avoids a migration and a nullable
    foreign key on a table that currently has neither.
    """
    await _get_room_for_participant(db, room_id, user)
    records = await fact_check_repo.list_for_room(db, room_id)
    return [FactCheckRead.model_validate(record) for record in records]


async def request_fact_check(
    db: AsyncSession,
    room_id: uuid.UUID,
    user: User,
    claim: str,
    *,
    provider: FactCheckProvider,
    settings: Settings,
) -> FactCheckRead:
    """Check one claim and record the verdict.

    Raises rather than persisting when the claim cannot be checked, so a failed request
    leaves no trace that could later be mistaken for a real ``unverified`` result.
    """
    room = await _get_room_for_participant(db, room_id, user)
    if room.ended_at is not None:
        raise ConflictError("This debate has ended.")

    await _enforce_limits(db, room_id, settings)

    # The only thing that leaves this process. Nothing about the room, the opponent or the
    # conversation is sent with it.
    result = await provider.check(claim)

    verdict, explanation, sources = _apply_trust_filter(result)

    record = await fact_check_repo.add_fact_check(
        db,
        room_id=room_id,
        requester_id=user.id,
        claim=claim,
        verdict=verdict,
        explanation=explanation,
        sources=sources,
    )
    await db.commit()

    logger.info(
        "Fact-check recorded",
        extra={
            "room_id": str(room_id),
            "verdict": verdict.value,
            "source_count": len(sources),
        },
    )
    return FactCheckRead.model_validate(record)
