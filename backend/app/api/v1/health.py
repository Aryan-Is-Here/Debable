"""Health endpoint.

Reports liveness and whether Postgres is reachable. Returns 503 when the database is
down so a platform health check treats the instance as unhealthy.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.health import ComponentStatus, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service and database health",
    responses={503: {"model": HealthResponse, "description": "A dependency is unavailable."}},
)
async def health(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    database: ComponentStatus = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        database = "error"
        logger.error("Database health check failed", extra={"error": str(exc)})

    if database != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=database,
        database=database,
        env=settings.env,
        version=__version__,
    )
