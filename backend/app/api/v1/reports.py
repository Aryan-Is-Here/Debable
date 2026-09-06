"""The report endpoint.

``docs/05-api-specification.md`` specifies a bare ``POST /report``. This is
``POST /rooms/{room_id}/report`` instead, for the same reason ratings hang off a room: what
is being reported is conduct in a specific debate, and being in that room is what makes the
caller a witness. A top-level endpoint would have to take the room in the body and check it
anyway, with nothing gained. Recorded as a deliberate deviation in
``docs/PROJECT-HANDBOOK.md`` §6.

There is no ``GET``. Nothing in the MVP reads reports back — see ``app/models/report.py``.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.report import ReportCreate, ReportRead
from app.services import report as report_service

router = APIRouter(tags=["reports"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/rooms/{room_id}/report",
    response_model=ReportRead,
    summary="Report your opponent's conduct in a debate",
    responses={
        401: {"description": "Missing or invalid Clerk session token."},
        403: {"description": "You are not a participant in this debate."},
        404: {"description": "No such room."},
        409: {"description": "You have already reported this debate."},
        422: {"description": "Unknown category, or detail over 500 characters."},
    },
)
async def submit_report(
    room_id: uuid.UUID,
    payload: ReportCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ReportRead:
    """File a report against the other debater.

    Works during a live debate as well as after it — harassment is reported while it is
    happening, so unlike rating, this does not wait for the room to end.
    """
    return await report_service.submit(
        db, room_id, current_user, category=payload.category, detail=payload.detail
    )
