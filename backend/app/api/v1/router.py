"""Aggregates every v1 route under a single mountable router.

Feature routers (topics, match, rooms, ...) are added here as their phases land.
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)
