"""Health check response models."""

from typing import Literal

from pydantic import BaseModel, Field

ComponentStatus = Literal["ok", "error"]


class HealthResponse(BaseModel):
    """Liveness plus dependency status."""

    status: ComponentStatus = Field(description="Overall service status.")
    database: ComponentStatus = Field(description="Result of a trivial query against Postgres.")
    env: str = Field(description="Configured environment name.")
    version: str = Field(description="Application version.")
