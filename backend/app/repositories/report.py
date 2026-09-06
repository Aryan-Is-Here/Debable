"""Report persistence.

Insert and a single existence check, which is all a record with no workflow behind it needs.
There is no list function on purpose: nothing in the MVP reads these back, and adding a
query for a screen that does not exist would invite one.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


async def add_report(
    db: AsyncSession,
    *,
    room_id: uuid.UUID,
    reporter_id: uuid.UUID,
    reported_user_id: uuid.UUID,
    category: str,
    detail: str | None,
) -> Report:
    """Insert a report. Raises ``IntegrityError`` on a duplicate; the caller commits."""
    report = Report(
        room_id=room_id,
        reporter_id=reporter_id,
        reported_user_id=reported_user_id,
        category=category,
        detail=detail,
    )
    db.add(report)
    await db.flush()
    return report


async def get_report_by_reporter(
    db: AsyncSession, room_id: uuid.UUID, reporter_id: uuid.UUID
) -> Report | None:
    """The caller's own report of a debate, if they filed one."""
    return await db.scalar(
        select(Report).where(Report.room_id == room_id, Report.reporter_id == reporter_id)
    )
